import asyncore, socket

class http_client(asyncore.dispatcher):

    def __init__(self, host, port, path, method='GET'):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect( (host, port) )
        self.buffer = '%s %s HTTP/1.1\r\n\r\n' % (method, path)

    def handle_connect(self):
        pass

    def handle_close(self):
        self.close()

    def handle_read(self):
        print self.recv(8192)

    def writable(self):
        return (len(self.buffer) > 0)

    def handle_write(self):
        sent = self.send(self.buffer)
        self.buffer = self.buffer[sent:]

def main():
    c = http_client('www.google.com', 80, '/', 'GET')
    asyncore.loop()

if __name__ == "__main__":
  main()
