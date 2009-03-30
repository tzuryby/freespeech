
import rsa

public_key = {
    'e': 4323015506425070957L, 
    'n': 635685726408938941174827698601998590830662423214015296838631527475663642867L}
    
a = 'eJwNy7kRgDAQA8DclRAxJ92rHtwEOQH9Rzjdmb3eD2snnW2DQhtUiSmCijkUxYIc6haVknzkDAcs\ncgJMmfw8gO17PfcPCGkRzw=='
b = 'eJwVybERgDAMQ9E+k1BxVixsaYcsQU/B/hXk/uv+8bwYK4lUTrGDitolkjGd/AXpouCS0dO1rzWJ\nyyo0AyCZ7cYa9/kBBQkRyg=='

def _verify(cypher):
    return rsa.verify(cypher, public_key)

NUM_OF_USERS = int(_verify(a))
CONCURRENT_SESSIONS = int(_verify(b))


    
    