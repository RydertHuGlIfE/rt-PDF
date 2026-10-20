from PIL.Image import SAVE_ALL
from pypdf import PdfWriter, PdfReader, os
from PIL import Image

def merge_pdf(pdf_list, output_path):
    writer = PdfWriter()
    for pdf in pdf_list:
        writer.append(pdf)
        print(f"appended {pdf}")

    with open(output_path, "wb") as output_file:
        writer.write(output_file)
    print(f"success merge and save as {output_path}")



def split_pdf(input_path):
    reader = PdfReader(input_path)

    for page_num, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)

        output_filename = f"name {page_num + 1}.pdf"

        with open(output_filename, "wb") as output_file:
            writer.write(output_file)
            print(f"saved {output_filename}")


def convert_imagestopdf(image_input, output_pdf_path):
    if isinstance(image_input, str):
        image_paths= [image_input]
    
    elif isinstance(image_input, list):
        image_paths = image_input
    else:
        raise TypeError("image_input must be a string or a list of strings")

    
    if not image_paths:
        print("error no path provided")
        return 

    try:
        first_image = Image.open(image_paths[0]).convert('RGB')

        if len(image_paths) > 1:
            remaining_images = []
            for path in image_paths[1:]:
                if os.path.exist(path):
                    img = Image.open(path).convert('RGB')
                    print("merge queue", path)
                else:
                    print("no file found skiping", path)


            first_image.save(
                output_pdf_path, "PDF", SAVE_ALL=True, append_images=remaining_images
            )
            print("merge complete")
        else:
            first_image.save(output_pdf_path, 'PDF')
            print("file saved")
    except Exception as e:
        print(e)



    