import sys
import optparse

from sns.cont import consts as cont_const
from client.content.api import RawContentApi
from client.content.hark import HarkJsonlinesHandler


def main():
    p = optparse.OptionParser(
        description=r"""content mgmt client""",
        prog="content main",
        version="0.1",
        usage=""" %prog [OPTION] """,
        )
    p.add_option("--file", "-f", action="store",
                 help="the data file.")
    p.add_option("--type", "-t", action="store", default='1000',
                 help="content source type: 1000 - Hark, 1001 - Examiner.")
    p.add_option("--size", "-s", action="store", default='0',
                 help="number of lines to process, default to all.")
    p.add_option("--db", "-d", action="store", default='True',
                 help="false to skip db update.")
    options = p.parse_args()[0]
    input_file = options.file
    content_type = int(options.type)
    size = int(options.size)
    db_update = bool(options.db)
    if not size:
        size = sys.maxint 
    if content_type == cont_const.CS_HARK:
        handler = HarkJsonlinesHandler(file_path=input_file)
        db = RawContentApi()
        while handler.total_count < size and not handler.eof:
            clips = handler.read()
            print "%d bad out of total %d. %d good out of %d in batch." % (handler.bad_count, handler.total_count, len(clips), handler.chunk_size)
            if db_update:
                obj = {'cskey': cont_const.CS_HARK,
                       'contents': str(clips),
                       }
                db.create(obj)


if __name__ == "__main__":
    main()
