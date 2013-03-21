## exifpy.__main__

import sys
import optparse
import logging

from . import process_file, FIELD_TYPES


def main():
    ## A proper OptionParser...
    option_parser = optparse.OptionParser(
        usage='%prog [options] file1.jpg [file2.jpg ...]',
        description='Extract EXIF information from digital camera image files.'
    )
    option_parser.add_option(
        '-q', '--quick', action='store_true', dest='quick', default=False,
        help='Do not process MakerNotes')
    option_parser.add_option(
        '-t', '--stop-tag', action='store', dest='stop_tag', metavar='TAG',
        help='Stop processing when this tag is retrieved')
    option_parser.add_option(
        '-s', '--strict', action='store_true', dest='strict', default=False,
        help='Run in strict mode (stop on errors)')
    option_parser.add_option(
        '-d', '--debug', action='store_true', dest='debug', default=False,
        help='Run in debug mode (display extra info)')
    option_parser.add_option(
        '-f', '--format', action='store', dest='format', default='human',
        help='Specify the desired output format. Allowed values are: '
             'human (the default), json, csv.')
    option_parser.add_option(
        '--color', action='store', dest='color', default='auto',
        help='Whether to colorize human-readable output. Allowed values are: '
             'auto (the default), never, always.')
    opts, args = option_parser.parse_args()

    ## Configure the logger
    logger = logging.getLogger('exifpy')
    logger.addHandler(logging.StreamHandler(sys.stderr))
    if opts.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    ## Prepare configuration from options
    detailed = not opts.quick
    stop_tag = opts.stop_tag or 'UNDEF'
    strict = opts.strict

    if opts.color == 'auto':
        use_colors = sys.stdout.isatty()

    else:
        use_colors = opts.color == 'always'

    ## Output info for each file
    if opts.format == 'human':

        if use_colors:
            message_format = \
                "  \x1b[1;36m{}\x1b[0m \x1b[0;36m({})\x1b[0m" \
                " = \x1b[1;32m{}\x1b[0m"
            filename_format = '\x1b[1m{}\x1b[0m'
        else:
            message_format = "  {} ({}) = {}"
            filename_format = '{}'

        for filename in args:
            print(filename_format.format(filename))

            try:
                fileobj = open(str(filename), 'rb')
            except IOError:
                print("  Unreadable file. Skipping.")
                continue

            ## Get the tags from file..
            data = process_file(
                fileobj,
                stop_tag=stop_tag,
                details=detailed,
                strict=strict)

            # if not data:
            #     print("  No EXIF information found")
            #     continue

            for key, value in sorted(data.iteritems()):

                if key in ('JPEGThumbnail', 'TIFFThumbnail'):
                    printable = '<binary-object>'
                    field_type = 'blob'
                else:
                    printable = repr(value.printable)
                    try:
                        field_type = FIELD_TYPES[value.field_type][2]
                    except IndexError:
                        field_type = 'unknown'

                print(message_format.format(key, field_type, printable))

    elif opts.format == 'json':
        ## We have some issues with this.. need work on the library
        raise NotImplementedError('JSON output not implemented yet')

    elif opts.format == 'csv':
        ## We have some issues with this.. need work on the library
        raise NotImplementedError('CSV output not implemented yet')


if __name__ == '__main__':
    main()
