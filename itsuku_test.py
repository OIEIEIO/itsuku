import pytest
from itsuku import *

def test_phi():
    # it shoud fail if the seed is not 4 bytes long
    seed = int_to_4bytes(123)
    seed_3bytes = seed[:3]
    seed_8bytes = seed+seed

    assert len(seed_3bytes) == 3
    assert len(seed_8bytes) == 8

    with pytest.raises(AssertionError):
        phi(seed_3bytes, 4)
    with pytest.raises(AssertionError):
        phi(seed_8bytes, 4)

    # it should return the same result using the high-level or low level algorithm
    assert phi(seed, 4, method='high-level') == phi(seed, 4, method='low-level')
    assert phi(seed, 28, method='high-level') == phi(seed, 28, method='low-level')
    assert phi(seed, 1024, method='high-level') == phi(seed, 1024, method='low-level')

    # it should return a value phi(i) inferior to i
    assert phi(seed, 2) < 2
    assert phi(seed, 4) < 4
    assert phi(seed, 256) < 256
    assert phi(seed, 1024) < 1024


def test_phis():
    seed = int_to_4bytes(256)

    # it should output an array of length n
    for n in range(1,12):
        assert len(phis(seed, 10, n)) == n

    # TODO : more tests, probably

def test_H():
    # it should return a bytes array of length M
    x = int_to_4bytes(123456)
    for i in range(1,15):
        assert len(H(i,x)) == i # TODO : check 0<
    
    # the H function should output the last M bytes of the sha512 hash of i
    for i in range(1,15):
        sha = sha512() # resetting the sha function
        sha_input = int_to_4bytes(i)
        sha.update(sha_input)
        assert sha.digest()[:10] == H(10,sha_input)
        


def test_int_to_4bytes():
    # it should always return a 4 bytes string
    assert len(int_to_4bytes(0)) == 4
    assert len(int_to_4bytes(1)) == 4
    assert len(int_to_4bytes(10)) == 4
    assert len(int_to_4bytes(1024)) == 4
    assert len(int_to_4bytes(4294967295)) == 4
    assert isinstance(int_to_4bytes(0), bytes)

    # it should return the expected hex bytes string, in a big endian order 
    assert int_to_4bytes(0) == b"\x00\x00\x00\x00"
    assert int_to_4bytes(1) == b"\x00\x00\x00\x01"
    assert int_to_4bytes(2) == b"\x00\x00\x00\x02"
    assert int_to_4bytes(16) == b"\x00\x00\x00\x10"
    assert int_to_4bytes(256) == b"\x00\x00\x01\x00"

def test_memory_build():
    M = 64
    x = 64
    T = 2**5
    I = os.urandom(M)

    for P in [1,2,4]:
        l = T//P
        for n in range(2,min(12,l)): # it should work for different values of n. n can't get bigger than l, otherwise the n "seeds" cannot fit in a slice
            X = memory_build(I, T, n, P, M)

            # Initialization steps
            for p in range(P):
                for i in range(n):
                    hash_input = int_to_4bytes(i) + int_to_4bytes(p) + I
                    assert X[p*l+i] == H(x, hash_input)

            # Construction steps
            for p in range(P):
                for i in range(n,l):
                    seed = X[p*l+i-1][:4] # seed that is used at each step is the 
                                          # 4 first bytes of the previous array item
                    
                    # asserting that the 0<=phi_k(i)<i condition is actually verified
                    phi_k = phis(seed,i,n)
                    for phi_k_i in phi_k:
                        assert phi_k_i < i
                        assert 0 < phi_k_i

                    hash_input = b""
                    for phi_k_i in phi_k:
                        hash_input += X[p*l+phi_k_i]
                    
                    # asserting the validity of the constructed item
                    assert X[p*l+i] == H(x, hash_input)

def test_merkle_tree():
    M = 64
    T = 2**5
    n = 2
    I = os.urandom(M)
    
    for P in [1,2,4]:
        l = T//P
        for n in range(2,min(12,l)): # should work for different values of n
            X = memory_build(I, T, n, P, M)
            
            MT = merkle_tree(I, X, M)
    
            # asserting the length is 2*T-1
            assert len(MT) == 2*T-1
            # asserting the end of the MT is actually the hashed original array
            assert MT[-T:] == [H(M,x) for x in X]
            # asserting the constructed items are the hash of their sons
            for i in range(T-1):
                assert MT[i] == H(M, MT[2*i+1]+MT[2*i+2]+I)
        
        # test on a particular case : if the initial array is constant,
        # then each "floor" of the merkle tree should be constant
        X0 = [int_to_4bytes(0)]*T
        MT0 = merkle_tree(I, X0, M)
    
        # iterating over the floors
        for i in range(1,int(log(T,2))):
            #remembering the value that we expect to find all over the floor
            value = MT0[(2**i)-1]
            # iterating inside the floor
            for j in range((2**i)-1, (2**(i-1))-2):
                assert MT0[i] == value

def test_compute_merkle_tree_node():
    M = 64
    I = os.urandom(M)

    # basic examples
    assert compute_merkle_tree_node(0, {0: b'\x00'*64}, I, 1, M) == b'\x00'*64
    assert compute_merkle_tree_node(0, {2: b'\x00'*64, 3: b'\x11'*64, 4: b'\xff'*64}, I, 4, M) == H(64, H(64, b'\x11'*64 + b'\xff'*64 + I) + b'\x00'*64 + I)
    assert compute_merkle_tree_node(1, {2: b'\x00'*64, 3: b'\x11'*64, 4: b'\xff'*64}, I, 4, M) == H(64, b'\x11'*64 + b'\xff'*64 + I)
    assert compute_merkle_tree_node(1, {3: b'\x11'*64, 4: b'\xff'*64}, I, 4, M) == H(64, b'\x11'*64 + b'\xff'*64 + I)

    # should be able to compute anything if all nodes are known
    T = 2**5
    n = 2
    
    for P in [1,2,4]:
        l = T//P
        for n in range(2,min(12,l)): # should work for different values of n
            X = memory_build(I, T, n, P, M)
            MT = merkle_tree(I, X, M)

            known_nodes = { i:v for i,v in enumerate(MT) }

            for i in range(len(MT)):
                assert compute_merkle_tree_node(i, known_nodes, I, T, M) == MT[i]

            # Now let's try and remove information while remaining computable
            for k in range(T-1):
                known_nodes = { i:v for i,v in enumerate(MT) if i>k}
                for i in range(k+1):
                    # the k first elements of the MT have been removed from known_nodes,
                    # they should be properly computed nonetheless
                    assert compute_merkle_tree_node(i, known_nodes, I, T, M) == MT[i]

    # should throw an error if it gets outside of the expected bounds
    with pytest.raises(AssertionError):
        assert compute_merkle_tree_node(1, {0: b'\x00'*64}, I, 1, M) == b'\x00'*64
    with pytest.raises(AssertionError):
        assert compute_merkle_tree_node(7, {2: b'\x00'*64, 3: b'\x11'*64, 4: b'\xff'*64}, I, 4, M) == H(64, H(64, b'\x11'*64 + b'\xff'*64 + I) + b'\x00'*64 + I)
    with pytest.raises(AssertionError): 
        assert compute_merkle_tree_node(1, {0: b'\x00'*64}, I, 2, M) == b'\x00'*64

def test_xor():
    assert xor(b"\x00", b"\x00") == b"\x00"
    assert xor(b"\x01", b"\x00") == b"\x01"
    assert xor(b"\x00", b"\x01") == b"\x01"
    assert xor(b"\x01", b"\x01") == b"\x00"

def test_compute_Y():
    M = 64
    T = 2**5
    S = 64
    L = ceil(3.3*log(T,2))
    I = os.urandom(M)
    
    for P in [1,2,4]:
        l = T//P
        for n in range(2,min(12,l)): # should work for different values of n
            X = memory_build(I, T, n, P, M)
            MT = merkle_tree(I, X, M)
            PSI = MT[0]
            N = os.urandom(32) # nounce

            Y, OMEGA, i = compute_Y(I, X, L, S, N, PSI)

            # asserting length
            assert len(Y) == L+1
            assert len(i) == L
            # verifying Y[0] is built as expected
            assert Y[0] == H(S, N + PSI + I)
            # verifying Y is correctly constructed
            for j in range(1,L+1):
                assert i[j-1] == int.from_bytes(Y[j-1], 'big') % T
                assert Y[j] == H(S, Y[j-1] + xor(X[i[j-1]], I))

def test_is_PoW_solved():
    assert is_PoW_solved(b'\x00'*64, b'\x00'*63 + b'\x01') == True
    assert is_PoW_solved(b'\x00'*64, b'\x00'*64) == False
    assert is_PoW_solved(b'\xff'*63 + b'\xfe', b'\xff'*64) == True

    with pytest.raises(AssertionError):
        is_PoW_solved(b'\x00', b'\x00'*64)
    with pytest.raises(AssertionError):
        is_PoW_solved(b'\x00', b'\x00')
    with pytest.raises(AssertionError):
        is_PoW_solved(b'\x00'*64, b'\x00')

def test_build_L():
    M = 64
    T = 2**5
    S = 64
    L = ceil(3.3*log(T,2))
    I = os.urandom(M)
     
    for P in [1,2,4]:
        l = T//P
        for n in range(2,min(12,l)): # should work for different values of n
            X = memory_build(I, T, n, P, M)
            MT = merkle_tree(I, X, M)
            PSI = MT[0]
            N = os.urandom(32) # nounce
            Y, OMEGA, i = compute_Y(I, X, L, S, N, PSI)

            round_L = build_L(i, X, P, n)
            
            for i_j in i:
                assert len(round_L[i_j]) == n
                p = i_j // l
                if i_j % l < n:
                    # assert correct construction
                    assert round_L[i_j] == X[p*l:p*l+n]
                    
                    # by construct, X[i_j] should be part of round_L[i_j]
                    assert X[i_j] in round_L[i_j]

                    # assert that the elements of round_L are actually computable
                    for k in range(0,n):
                        stuff_to_hash = int_to_4bytes(k) + int_to_4bytes(p) + I
                        assert round_L[i_j][k] == H(M, stuff_to_hash)

                else:
                    seed = X[i_j-1][:4]
                    # assert correct construction
                    assert round_L[i_j] == [ X[p*l + phi_k_i] for phi_k_i in phis(seed, i_j%l, n) ]

                    # make sure X[i_j] can be recomputed using the elements of round_L[i_j]
                    hash_input = b""
                    for item in round_L[i_j]:
                        hash_input += item
                    assert H(M,hash_input) == X[i_j]

def test_provided_indexes():
    M = 64
    T = 2**5
    S = 64
    L = ceil(3.3*log(T,2))
    I = os.urandom(M)
     
    for P in [1,2,4]:
        l = T//P
        for n in range(2,min(12,l)): # should work for different values of n
            X = memory_build(I, T, n, P, M)
            MT = merkle_tree(I, X, M)
            PSI = MT[0]
            N = os.urandom(32) # nounce
            Y, OMEGA, i = compute_Y(I, X, L, S, N, PSI)
            round_L = build_L(i, X, P, n)

            indexes = provided_indexes(round_L, P, T, n)

            for index in indexes:
                assert index < T

            for i_j in i:
                # all the i_j should be in indexes as X[i_j] can alwas be recomputed
                # using only the elements of round_L[i_j]. Thus, X[i_j] can and must
                # be considered as a given if round_L is known
                assert i_j in indexes
                
                p = i_j // l
                
                if i_j % l < n :
                    # case where the elements of round[i_j] were computed at step (1.a)
                    for k in range(p*l, p*l+n):
                        assert k in indexes
                else :
                    # case where the elements of round[i_j] were computed at step (1.b)

                    seed = round_L[i_j][0][:4]

                    # The seed computed using round_L should be the same seed as the
                    # one used during the construction of X
                    assert seed == X[i_j - 1][:4]
                    for index in [p*l+phi_k_i for phi_k_i in phis(seed, i_j % l, n)]:
                        assert index in indexes
                
            # Asserting there are no duplicates
            assert len(indexes) == len(set(indexes))

def test_build_Z():
    M = 64
    T = 2**5
    S = 64
    L = ceil(3.3*log(T,2))
    I = os.urandom(M)
    
    for P in [1,2,4]:
        l = T//P
        for n in range(2,min(12,l)): # should work for different values of n
            X = memory_build(I, T, n, P, M)
            MT = merkle_tree(I, X, M)
            PSI = MT[0]
            N = os.urandom(32) # nounce
            Y, OMEGA, i = compute_Y(I, X, L, S, N, PSI)
            round_L = build_L(i, X, P, n)
            
            Z = build_Z(round_L, MT, P, T, n)

            # A shift has to be applied so the indexes match those of the
            # Merkle Tree and not those of X.
            indexes = [ index + T - 1 for index in  provided_indexes(round_L, P, T, n)]

            for k in Z:
                assert k not in indexes
                assert Z[k] == MT[k]
                if k >= T-1:
                    assert Z[k] == H( M, X[k-(T-1)] )
            
            assert set(Z.keys()) == set(opening(T, provided_indexes(round_L, P, T, n)))

def clean_Z():
    Z = { 5: b'\x00', 8: b'\xfe', 14: b'\xa4' }
    cleaned_Z = clean_Z(Z)
    assert len(cleaned_Z) == 3
    for k in Z:
        assert cleaned_Z[k] == Z[k].hex()

def test_trim_round_L():
    with pytest.raises(AssertionError):
        trim_round_L({}, 5, 2, 0)
    
    # Assert that the intended items are trimmed off of the dict
    round_L_1 = {7: [], 15:[]} # should remain unchanged if (P, T, n) = (32, 4, 6)
    round_L_2 = {5: [], 10:[]} # should be totally trimmed
    round_L_3 = {6: [], 14:[]} # edge case : should remain unchanged
    round_L_4 = {5: [], 15:[]} # should be partially modified

    assert trim_round_L(round_L_1 , 4, 32, 6) == round_L_1
    assert trim_round_L(round_L_2 , 4, 32, 6) == {}
    assert trim_round_L(round_L_3 , 4, 32, 6) == round_L_3
    assert trim_round_L(round_L_4 , 4, 32, 6) == {15:[]}

    # Assert that the bytearrays are properly converted
    round_L_5 = {7: [b'\x00', b'\xfe', b'\xa4']}
    assert trim_round_L(round_L_5, 4, 32, 6) == {7: ['00','fe','a4']}

def test_build_JSON_output():
    JSON = build_JSON_output(N=b'\x00'*63 + b'\xff', round_L={}, Z={}, P=4, T=32, n='n', I=b'\xff'*64, M='M', L='L', S='S', d=b'\x00'*64)
    
    data = json.loads(JSON)
    
    assert data['answer']['N'] == '00'*63 + 'ff'
    assert data['answer']['round_L'] == {}
    assert data['answer']['Z'] == {}

    assert data['params']['P'] == 4
    assert data['params']['T'] == 32
    assert data['params']['n'] == 'n'
    assert data['params']['I'] == 'ff'*64
    assert data['params']['M'] == 'M'
    assert data['params']['L'] == 'L'
    assert data['params']['S'] == 'S'
    assert data['params']['d'] == '00'*64

#@pytest.mark.skip(reason="not good yet")
def test_PoW(): 
    M = 64
    T = 2**4
    S = 64
    L = ceil(3.3*log(T,2))
    I = os.urandom(M)
    d = b'\x00'*64 # minimal difficulty

    for P in [1,2,4]:
        l = T//P
        for n in range(2,min(12,l)): # should work for different values of n 
            json_output = PoW(I=I, T=T, n=n, P=P, M=M, L=L, S=S, d=d)
            data = json.loads(json_output)

            assert data['params']['P'] == P
            assert data['params']['T'] == T
            assert data['params']['n'] == n
            assert data['params']['I'] == I.hex()
            assert data['params']['M'] == M
            assert data['params']['L'] == L
            assert data['params']['S'] == S
            assert data['params']['d'] == d.hex()
            
            # Verifying the answer
            
            N = data['answer']['N']
            unprocessed_Z = data['answer']['Z']
            unprocessed_round_L = data['answer']['round_L']
           
            # Preparing round_L
            round_L = {}
            for k in unprocessed_round_L:
                round_L[int(k)] = [ int(x, 16).to_bytes(64, 'big') for x in unprocessed_round_L[k] ]

            # Preparing Z
            Z = {}
            for k in unprocessed_Z:
                Z[int(k)] = int(unprocessed_Z[k], 16).to_bytes(64, 'big')

            # Verifications
            for k in round_L:
                assert k+(T-1)>=T
                assert k+(T-1) not in Z

            # Building back X
            X = [None]*T
            #TODO : be more efficient on memory
            for i_j in round_L:
                p = i_j//l

                # Building X[i_j]
                hash_input = b''
                for x in round_L[i_j]:
                    hash_input += x
                X[i_j] = H(M, hash_input)

                # Building its antecedents
                seed = round_L[i_j][0][:4]
                phi_i = phis(seed, i_j%l, n)
                for k, x in enumerate(round_L[i_j]):
                   X[p*l + phi_i[k]] = x

            # Building all elements that were built at step 1.a
            for p in range(P):
                for i in range(n):
                    X[p*l + i] = H(M, int_to_4bytes(i) + int_to_4bytes(p) + I)
           
            # This stores the elements of the previously built X in a dictionary,
            # With a structure similira to { index: X[index]} with uncomputed elements
            # (those for which X[index} == None) removed
            X_dict = {k: v for k,v in enumerate([x for x in X if x != None])}
            
            for x in X_dict:
                assert x != None

            # Let's build a dict of all the nodes we know (round_L, Z, and the precomputable ones), that satisfies the requirement of compute_merkle_tree_node
            known_nodes = {**Z, **{ k + (T-1) : H(M,v) for k,v in X_dict.items() } }
            print([ i + (T-1) for i in X_dict.keys() ])
            print(Z.keys())
            print(sorted(known_nodes.keys()))

            # Verifications
            assert len(known_nodes) == len(Z) + len(X_dict)

            OMEGA = compute_merkle_tree_node(0, known_nodes, I, T, M)
            
            # We can now use the previous functions to compute i and OMEGA
            Y, OMEGA, computed_i = compute_Y(I, X, L, S, N, PSI)
            
            # Verifying the two conditions that define the success of the PoW :
            #
            # 1. OMEGA satisfies the difficulty constraint
            assert is_PoW_solved(d, OMEGA) == True
            # 2. The keys of round_L correspond the i that has been computed by compute_Y
            assert computed_i == list(round_L.keys())
