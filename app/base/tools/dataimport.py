import io
import csv

WS_ALLOWED_IMPORT_EXT = "csv"
WS_ALLOWED_COLUMNS = 3


def allowed_file(filename):
    return '.' in filename and \
           (filename.endswith(WS_ALLOWED_IMPORT_EXT) or filename.endswith(WS_ALLOWED_IMPORT_EXT.upper()))


def read_csv(file):
    """
    Read csv file of format (video_path, tc_start, tc_end), and return list of corresponding keyframes.
    :parameter file: uploaded csv file
    """
    data_set = file.read().decode('UTF-8')
    io_string = io.StringIO(data_set)

    num_cols = len(next(io_string).split(","))
    data = []

    if WS_ALLOWED_COLUMNS == num_cols:

        allowed_cols = True
        try:
            for line in csv.reader(io_string, delimiter=',', quotechar="|"):
                video_name, tc_start, tc_end = [x for x in line]

                data.append([video_name, convert_tc2frame(tc_start), convert_tc2frame(tc_end)])
        except ValueError:
            pass

    else:
        allowed_cols = False

    return data, allowed_cols


def convert_tc2frame(tc):
    return int(25 / 1000 * int(tc))
