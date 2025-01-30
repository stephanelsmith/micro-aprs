import io
import asyncio
import traceback

class CustomStream(io.IOBase):
    def __init__(self):
        self.buffer = io.BytesIO()
    
    def write(self, data):
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("Expected bytes or bytearray")
        self.buffer.write(data)
        return len(data)
    
    def read(self, size=-1):
        return self.buffer.read(size)
    
    def readline(self):
        return self.buffer.readline()
    
    def seek(self, offset, whence=io.SEEK_SET):
        return self.buffer.seek(offset, whence)
    
    def tell(self):
        return self.buffer.tell()
    
    def close(self):
        self.buffer.close()
    
    def readable(self):
        return True
    
    def writable(self):
        return True
    
    def seekable(self):
        return True

async def producer(rio):
    try:
        while True:
            print('w')
            rio.write(b'hello')
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        raise
    except Exception as err:
        traceback.print_exception()

async def consumer(rio):
    try:
        stream = asyncio.StreamReader(rio)
        while True:
            print('wait...')
            r = await stream.read(1)
            print(r)
    except asyncio.CancelledError:
        raise
    except Exception as err:
        traceback.print_exception()

async def main():
    tasks = []
    rio = CustomStream()
    tasks.append(asyncio.create_task(producer(rio)))
    tasks.append(asyncio.create_task(consumer(rio)))
    await asyncio.gather(*tasks, return_exceptions=True)
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
# Example usage
# if __name__ == "__main__":
    # stream = CustomStream()
    # stream.write(b"Hello, World!\n")
    # stream.seek(0)
    # print(stream.read())  # Output: b'Hello, World!\n'

    # # Example usage with asyncio StreamReader
    # async def use_custom_stream_with_reader():
        # stream = CustomStream()
        # stream.write(b"Async Hello, World!\n")
        # stream.seek(0)
        
        # reader = asyncio.StreamReader()
        # while data := stream.read(1024):
            # reader.feed_data(data)
        # reader.feed_eof()
        
        # result = await reader.read()
        # print(result)  # Output: b'Async Hello, World!\n'
    
    # asyncio.run(use_custom_stream_with_reader())

