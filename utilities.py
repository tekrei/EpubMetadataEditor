from ebooklib import epub
import glob
import os


DEFAULT_NAMESPACE = "DC"


def get_epub_files(folder):
    return glob.glob(folder + "/*.epub")


def get_filename(file):
    return os.path.basename(file)


def get_metadata(file_path, keys, namespace=DEFAULT_NAMESPACE):
    book = get_epub(file_path)
    values = []
    for key in keys:
        try:
            value = book.get_metadata(namespace, key)
            if value:
                values.append(",".join([v[0] for v in value]))
                continue
        except BaseException:
            pass
        values.append("")
    return values


def update_book_metadata(file_path, key, value, namespace=DEFAULT_NAMESPACE):
    book = get_epub(file_path)
    book.metadata[epub.NAMESPACES[namespace]][key] = [(value, {})]
    epub.write_epub(file_path, book)


def get_epub(file_path):
    try:
        return epub.read_epub(file_path)
    except BaseException as e:
        print(e)
        return None
