## exifpy.__main__

from . import process_file, FIELD_TYPES

# show command line usage
def usage(exit_status):
    msg = 'Usage: EXIF.py [OPTIONS] file1 [file2 ...]\n'
    msg += 'Extract EXIF information from digital camera image files.\n\nOptions:\n'
    msg += '-q --quick   Do not process MakerNotes.\n'
    msg += '-t TAG --stop-tag TAG   Stop processing when this tag is retrieved.\n'
    msg += '-s --strict   Run in strict mode (stop on errors).\n'
    msg += '-d --debug   Run in debug mode (display extra info).\n'
    print(msg)
    sys.exit(exit_status)

# library test/debug function (dump given files)
if __name__ == '__main__':
    import sys
    import getopt

    # parse command line options/arguments
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hqsdt:v", ["help", "quick", "strict", "debug", "stop-tag="])
    except getopt.GetoptError:
        usage(2)
    if args == []:
        usage(2)
    detailed = True
    stop_tag = 'UNDEF'
    debug = False
    strict = False
    for o, a in opts:
        if o in ("-h", "--help"):
            usage(0)
        if o in ("-q", "--quick"):
            detailed = False
        if o in ("-t", "--stop-tag"):
            stop_tag = a
        if o in ("-s", "--strict"):
            strict = True
        if o in ("-d", "--debug"):
            debug = True

    # output info for each file
    for filename in args:
        try:
            file=open(str(filename), 'rb')
        except:
            print("'%s' is unreadable\n"%filename)
            continue
        print(filename + ':')
        # get the tags
        data = process_file(file, stop_tag=stop_tag, details=detailed, strict=strict, debug=debug)
        if not data:
            print('No EXIF information found')
            continue

        x=data.keys()
        x.sort()
        for i in x:
            if i in ('JPEGThumbnail', 'TIFFThumbnail'):
                continue
            try:
                print('   %s (%s): %s' % \
                      (i, FIELD_TYPES[data[i].field_type][2], data[i].printable))
            except:
                print('error', i, '"', data[i], '"')
        if 'JPEGThumbnail' in data:
            print('File has JPEG thumbnail')
