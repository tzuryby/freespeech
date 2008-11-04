
__all__ = ['printargs']

def printargs(fn, *args, **kwargs):
    def wrapper(*args, **kwargs):
        print 'function name:', fn.__name__
        print 'args:', args
        print 'kwargs:', kwargs        
        return fn(*args, **kwargs)
    
    return wrapper
    
if __name__ == '__main__':
    @printargs
    def bar(a,b,c):
        print 'Hello'
        
    bar(1,2,3)