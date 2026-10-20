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


def split_pdf(input_path, output_dir=None):
    """Splits each page of input_path into a separate PDF file."""
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
            print(f"saved {output_filename}")
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