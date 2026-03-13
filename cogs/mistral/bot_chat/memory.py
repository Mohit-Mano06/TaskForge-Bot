memory_buffer = []

MAX_MEMORY = 8


def add_memory(message):
    memory_buffer.append(message)

    if len(memory_buffer) > MAX_MEMORY:
        memory_buffer.pop(0)


def get_memory():
    return "\n".join(memory_buffer)