import os
from PIL import Image
from pypdf import PdfWriter, PdfReader


def merge_pdf(pdf_list, output_path):
    """Merges a list of PDF filepaths into a single output PDF."""
    if not pdf_list:
        raise ValueError("No PDF files provided to merge.")

    writer = PdfWriter()
    for pdf in pdf_list:
        if os.path.exists(pdf):
            writer.append(pdf)
            print(f"appended {pdf}")
        else:
            print(f"File not found, skipping: {pdf}")

    with open(output_path, "wb") as output_file:
        writer.write(output_file)
    print(f"success merge and save as {output_path}")
    return output_path


def parse_page_ranges(range_str: str, total_pages: int):
    """
    Parses a string like '1-10, 11-29, 30-39' or '1-29, 30' into a list of (start, end) 1-based tuples.
    """
    ranges = []
    parts = [p.strip() for p in range_str.split(",") if p.strip()]

    for part in parts:
        if "-" in part:
            sub = part.split("-", 1)
            start_str = sub[0].strip()
            end_str = sub[1].strip()

            start = int(start_str) if start_str else 1
            end = int(end_str) if end_str else total_pages
        else:
            start = int(part)
            end = start

        start = max(1, min(start, total_pages))
        end = max(1, min(end, total_pages))
        if start > end:
            start, end = end, start

        ranges.append((start, end))

    return ranges


def split_pdf_at_page(input_path: str, split_page: int, output_dir: str = None):
    """
    Splits a PDF into 2 parts before and after split_page.
    Part 1: pages 1 to split_page (inclusive)
    Part 2: pages split_page + 1 to total_pages
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")

    reader = PdfReader(input_path)
    total_pages = len(reader.pages)
    base_name = os.path.splitext(os.path.basename(input_path))[0]

    if not output_dir:
        output_dir = os.path.dirname(input_path) or "."
    os.makedirs(output_dir, exist_ok=True)

    split_page = max(1, min(split_page, total_pages - 1))
    generated_files = []

    # Part 1 (pages 1 to split_page)
    w1 = PdfWriter()
    for i in range(0, split_page):
        w1.add_page(reader.pages[i])
    p1_suffix = f"pg1-{split_page}" if split_page > 1 else "pg1"
    f1 = os.path.join(output_dir, f"{base_name}_part1_{p1_suffix}.pdf")
    with open(f1, "wb") as out:
        w1.write(out)
    generated_files.append(f1)

    # Part 2 (pages split_page + 1 to total_pages)
    w2 = PdfWriter()
    for i in range(split_page, total_pages):
        w2.add_page(reader.pages[i])
    p2_start = split_page + 1
    p2_suffix = f"pg{p2_start}-{total_pages}" if p2_start < total_pages else f"pg{total_pages}"
    f2 = os.path.join(output_dir, f"{base_name}_part2_{p2_suffix}.pdf")
    with open(f2, "wb") as out:
        w2.write(out)
    generated_files.append(f2)

    return generated_files


def split_pdf_by_cut_points(input_path: str, cut_points: list, output_dir: str = None):
    """
    Splits a PDF into N parts given cut_points.
    For example, cut_points=[29] -> 2 parts: (1, 29) and (30, total).
    cut_points=[10, 29] -> 3 parts: (1, 10), (11, 29), and (30, total).
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")

    reader = PdfReader(input_path)
    total_pages = len(reader.pages)

    # Clean and sort cut points within valid range [1, total_pages - 1]
    valid_cuts = sorted(list(set(
        max(1, min(int(c), total_pages - 1)) for c in cut_points
    )))

    if not valid_cuts:
        valid_cuts = [max(1, total_pages // 2)]

    ranges = []
    prev = 1
    for cut in valid_cuts:
        ranges.append((prev, cut))
        prev = cut + 1
    ranges.append((prev, total_pages))

    return split_pdf_by_ranges(input_path, ranges, output_dir=output_dir)


def split_pdf_by_ranges(input_path: str, page_ranges, output_dir: str = None):
    """
    Splits a PDF into multiple parts based on page_ranges (list of (start, end) 1-based tuples).
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")

    reader = PdfReader(input_path)
    total_pages = len(reader.pages)
    base_name = os.path.splitext(os.path.basename(input_path))[0]

    if not output_dir:
        output_dir = os.path.dirname(input_path) or "."
    os.makedirs(output_dir, exist_ok=True)

    generated_files = []
    for idx, (start, end) in enumerate(page_ranges):
        writer = PdfWriter()
        for p in range(start - 1, end):
            if 0 <= p < total_pages:
                writer.add_page(reader.pages[p])

        range_suffix = f"pg{start}-{end}" if start != end else f"pg{start}"
        filename = os.path.join(output_dir, f"{base_name}_part{idx + 1}_{range_suffix}.pdf")
        with open(filename, "wb") as out:
            writer.write(out)
        generated_files.append(filename)

    return generated_files


def split_pdf(input_path, output_dir=None, split_at=None, cut_points=None, ranges=None):
    """
    High-level split function:
    - If split_at is specified (e.g. 29): splits into 2 files before/after that page.
    - If cut_points is specified (e.g. [10, 29]): splits into N files at cut points.
    - If ranges is specified (e.g. [(1, 10), (11, 29), (30, 39)]): splits into those ranges.
    - If none: splits every page into individual single-page files.
    """
    if split_at is not None:
        return split_pdf_at_page(input_path, split_at, output_dir=output_dir)

    if cut_points is not None:
        return split_pdf_by_cut_points(input_path, cut_points, output_dir=output_dir)

    if ranges is not None:
        return split_pdf_by_ranges(input_path, ranges, output_dir=output_dir)

    # Fallback: extract every single page
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")

    reader = PdfReader(input_path)
    base_name = os.path.splitext(os.path.basename(input_path))[0]

    if not output_dir:
        output_dir = os.path.dirname(input_path) or "."
    os.makedirs(output_dir, exist_ok=True)

    generated_files = []
    for page_num, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)

        output_filename = os.path.join(output_dir, f"{base_name}_page_{page_num + 1}.pdf")
        with open(output_filename, "wb") as output_file:
            writer.write(output_file)
        generated_files.append(output_filename)

    return generated_files


def convert_imagestopdf(image_input, output_pdf_path):
    """Converts a single image or a list of image paths to a PDF."""
    if isinstance(image_input, str):
        image_paths = [image_input]
    elif isinstance(image_input, list):
        image_paths = image_input
    else:
        raise TypeError("image_input must be a string or a list of strings")

    if not image_paths:
        print("error no path provided")
        return False

    try:
        first_image = Image.open(image_paths[0]).convert('RGB')
        remaining_images = []

        if len(image_paths) > 1:
            for path in image_paths[1:]:
                if os.path.exists(path):
                    img = Image.open(path).convert('RGB')
                    remaining_images.append(img)
                    print("merge queue", path)
                else:
                    print("no file found skipping", path)

            first_image.save(
                output_pdf_path, "PDF", save_all=True, append_images=remaining_images
            )
            print("merge complete")
        else:
            first_image.save(output_pdf_path, 'PDF')
            print("file saved")
        return output_pdf_path
    except Exception as e:
        print(f"Error converting images to PDF: {e}")
        raise e