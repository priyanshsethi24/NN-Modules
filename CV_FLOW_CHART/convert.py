import fitz
import os

def convert_pdf_to_image(pdf_path, resolution=500):
    '''
    Convert the given pdf into images
    '''
    bn = os.path.basename(pdf_path)
    if 'pdf' in bn:
        bn = bn.replace('pdf', 'png')
    elif 'PDF' in bn:
        bn = bn.replace('PDF', 'png')
    else:
        bn = 'sample.png'

    name = bn

    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=resolution)
    pix.save(name)
    return name


if __name__=="__main__":
    pdf_path = "/home/mohit/converted_OrgChart 2.pdf"
    convert_pdf_to_image(pdf_path)