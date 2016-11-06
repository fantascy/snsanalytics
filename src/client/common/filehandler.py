import os


class JsonlinesHandler():
    def __init__(self, file_path, chunk_size=500):
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.total_count = 0
        self.bad_count = 0
        self.eof = False

    def read(self):
        lines = self.read_raw()
        return self.transform(lines) 

    def read_raw(self):
        if self.eof:
            print "EOF!"
            return [] 
        cursor_file_path = self.cursor_file_path()
        if os.path.exists(cursor_file_path):
            cf = open(self.cursor_file_path(), 'r+')
            cursor_str = cf.readline()
            cursor = long(cursor_str) if cursor_str else 0L
        else:
            cf = open(self.cursor_file_path(), 'w')
            cursor = 0L
        f = open(self.file_path, 'r')
        f.seek(cursor)
        lines = []
        for line_num in xrange(self.chunk_size):
            line = f.readline()
            if line is None or not line.endswith('\n'):
                self.eof = True
                print "EOF after reading %d lines." % line_num
                break
            else:
                lines.append(line)
        cursor = f.tell()
        f.close()
        cf.seek(0)
        cf.write(str(cursor))
        cf.close() 
        print "Cursor for next line is %d." % cursor
        self.total_count += len(lines)
        return lines

    def transform(self, lines):
        return lines

    def cursor_file_path(self):
        return "%s.cursor" % self.file_path




    

