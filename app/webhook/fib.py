memory = [0, 1]
def fib(x):
    if (x < 0):
        return -1
    if (x < len(memory)):
        return memory[x]
    memory.append(fib(x - 1) + fib(x - 2))
    return memory[x]