from docx import Document
import xml.etree.ElementTree as ET
from lxml import etree
from xml.sax.saxutils import escape
import zipfile
import os
from common.s3_operations import S3Helper
from common.logs import logger
import win32com.client
from pathlib import Path
import pythoncom
import re
from scripts.terminate_active_COM import terminate_active_processes

def find_git_root(start_path: Path) -> Path:
    """Finds the root of the Git repository by looking for the .git folder."""
    current_path = start_path.resolve()

    while current_path != current_path.parent:  # Stop at the drive root (C:\, D:\, etc.)
        if (current_path / ".git").exists():  # Check if .git folder exists
            return current_path
        current_path = current_path.parent  # Move up one level

    raise FileNotFoundError("Git repository root not found. Ensure the script is inside a Git repo.")

# Get the repo root (starting search from the script's location)
repo_root = find_git_root(Path(__file__).parent)
TMP_DIR = repo_root / "s3_downloads"

# Create the directory if it doesn’t exist
TMP_DIR.mkdir(parents=True, exist_ok=True)

# TMP_DIR = '/tmp'
# if not os.path.exists(TMP_DIR):
#     os.makedirs(TMP_DIR)

# def extract_bookmark_references(docx_path):
#     """
#     Extract bookmark references and associated names from a Word document (.docx).
    
#     Args:
#         docx_path (str): Path to the .docx file.
    
#     Returns:
#         tuple: A tuple containing two lists:
#             - references (list): List of bookmark names referenced in the document.
#             - names (list): List of associated names extracted from the document.
#     """
#     # Load the Word document
#     try:
#         if docx_path.startswith('s3'):
#             s3_bucket = docx_path.split('/')[2]
#             s3_helper = S3Helper(s3_bucket)
#             s3_key = '/'.join(docx_path.split('/')[3:])
#             local_file_path = os.path.join(TMP_DIR, os.path.basename(s3_key))
#                 # Download the file from S3
#             s3_helper.download_file_from_s3(s3_key, local_file_path)
#             docx_path =  local_file_path

#         logger.info(str(f'Starting extracting reference names ')+'[extract_bookmark_references] [scripts/check_doc_names.py:33]')
#         doc = Document(docx_path)
        
#         # Extract XML content from the document
#         xml_content = "".join(ET.tostring(part, encoding="unicode", method="xml") for part in doc.element.body.iter())
        
#         # Wrap the content in a root element to ensure well-formed XML
#         root = ET.fromstring(f"<root>{xml_content}</root>")

#         # Extract bookmark references
#         references = []
#         for instr in root.findall(".//w:instrText", namespaces={"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}):
#             if instr.text and "REF" in instr.text:
#                 parts = instr.text.split()
#                 if len(parts) > 1:
#                     references.append(parts[1])  # Extract the bookmark name

#         # Extract names associated with bookmarks
#         names = []
#         capture = False
#         current_name = []
        
#         for elem in root.iter():
#             tag = elem.tag
#             attrib = elem.attrib
#             text = elem.text

#             # Check for the start of a bookmark name
#             if tag == "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fldChar" and attrib.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fldCharType") == "separate":
#                 capture = True
#             # Check for the end of a bookmark name
#             elif tag == "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fldChar" and attrib.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fldCharType") == "end":
#                 capture = False
#                 if current_name:
#                     names.append("".join(current_name))
#                     current_name = []
#             # Collect text when within a bookmark name
#             elif capture and tag == "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t" and text:
#                 current_name.append(text)

#         logger.info(str('Extraction of references complete compiling into a list')+'[extract_bookmark_reference] [scripts/check_doc_names.py:74]')
#         llist = []
#         ulist = []
#         for r, n in zip(references, names):
#                 if r not in llist:
#                     ulist.append((r, n))
#                     llist.append(r)

#         logger.info(str(f'Extraction of references complete ')+'[extract_bookmark_reference] [scripts/check_doc_names.py:82]')
#         return ulist
    
#     except Exception as e:
#         logger.error(str(f'Encountered error while extracting references - {e}')+' [extract_bookmark_reference] [scripts/check_doc_names.py:86]')
#         raise Exception(str(f'{e}'))

def extract_bookmark_references(docx_path):
    """
    Extract bookmark references, associated names, and hyperlink texts from a Word document (.docx).
    
    Args:
        docx_path (str): Path to the .docx file.
    
    Returns:
        tuple: A tuple containing a list of tuples:
            - Bookmark name (str)
            - Associated name (str)
            - Hyperlink text (str) if present, otherwise None
    """
    try:
        if docx_path.startswith('s3'):
            s3_bucket = docx_path.split('/')[2]
            s3_helper = S3Helper(s3_bucket)
            s3_key = '/'.join(docx_path.split('/')[3:])
            local_file_path = os.path.join(TMP_DIR, os.path.basename(s3_key))
            s3_helper.download_file_from_s3(s3_key, local_file_path)
            docx_path = local_file_path

        logger.info('Starting extracting references and hyperlink text')
        # doc = Document(docx_path)

        # Extract XML content from the document
        with zipfile.ZipFile(docx_path, 'r') as z:
            with z.open('word/document.xml') as f:
                document_xml_content = f.read().decode('utf-8', errors='replace')

        # Remove XML declaration if it exists
        document_xml_content = re.sub(r'^<\?xml[^>]+\?>', '', document_xml_content).strip()

        # Wrap the cleaned XML content inside a <root> element
        wrapped_xml = f"<root>{document_xml_content}</root>"

        # Parse safely
        root = etree.fromstring(wrapped_xml)

        # Extract bookmark references
        references = []
        for instr in root.findall(".//w:instrText", namespaces={"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}):
            if instr.text and "REF" in instr.text:
                parts = instr.text.split()
                if len(parts) > 1:
                    references.append(parts[1])  # Extract the bookmark name

        # Extract names and hyperlink text associated with bookmarks
        names = []
        hyperlinks = []
        capture = False
        current_name = []

        for elem in root.iter():
            tag = elem.tag
            attrib = elem.attrib
            text = elem.text

            # Check for the start of a bookmark name
            if tag == "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fldChar" and attrib.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fldCharType") == "separate":
                capture = True
            # Check for the end of a bookmark name
            elif tag == "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fldChar" and attrib.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fldCharType") == "end":
                capture = False
                if current_name:
                    curr_name = "".join(current_name)
                    if len(curr_name) < 200:
                        names.append(curr_name)
                    else:
                        names.append("Invalid link format")
                    current_name = []
            # Collect text when within a bookmark name
            elif capture and tag == "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t" and text:
                current_name.append(text)

            # Check for hyperlinks
            elif tag == "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}hyperlink":
                anchor = attrib.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}anchor")
                if anchor:
                    hyperlink_text = "".join(
                        t.text for t in elem.findall(".//w:t", namespaces={"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"})
                    )
                    # print((anchor, hyperlink_text))
                    if len(hyperlink_text) >= 200:
                        hyperlink_text = "Invalid link format"
                    hyperlinks.append((anchor, hyperlink_text))

        logger.info('Extraction complete, compiling into a list')
        # print(f'Refernces: {references}, names: {names}')
        # Combine bookmarks, names, and hyperlinks
        result = set()
        for h in hyperlinks:
            result.add(h)

        llist = []
        # ulist = []
        for r, n in zip(references, names):
                if r not in llist:
                    n = re.sub(r'[\u200e\u200f\u202a\u202b\u202c\u202d\u202e]', '', n)
                    result.add((r, n))
                    llist.append(r)
        
        # print(result)
        logger.info('Extraction complete')
        return result

    except Exception as e:
        logger.error(f'Encountered error while extracting references: {e}')
        raise Exception(str(e))
    
def extract_links_and_references_pages(doc_path):
    # Initialize Word application
    try:
        terminate_active_processes()
        pythoncom.CoInitialize()
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False  # Keep Word application hidden
        print("Word Opened")
        doc = word.Documents.Open(doc_path)
        word.ActiveDocument.Repaginate()
        results = []
        print("Iterating over links")
        # Iterate over hyperlinks
        if doc.hyperlinks.Count > 0:
            for hyperlink in doc.Hyperlinks:
                link_text = hyperlink.TextToDisplay
                address = hyperlink.Address if hyperlink.Address else f"Internal: {hyperlink.SubAddress}"
                try:
                    anchor_range = hyperlink.Range
                    page_number = anchor_range.Information(3)
                except Exception as e:
                    continue
                print(page_number)  # wdActiveEndPageNumber
                results.append({
                    "type": "Hyperlink",
                    "page_number": page_number,
                    "link_text": link_text,
                    "target": address
                })
        
        print("Iterating over cross-refs")
        # Iterate over fields for cross-references
        for field in doc.Fields:
            if field.Type == 3:  # wdFieldRef (Cross-reference)
                ref_text = field.Result.Text
                target_range = field.Result
                target_text = field.Code.text if target_range else "No target text"
                anchor_range = field.Code
                page_number = anchor_range.Information(3)  # wdActiveEndPageNumber
                results.append({
                    "type": "Cross-reference",
                    "page_number": page_number,
                    "ref_text": ref_text,
                    "target_text": target_text
                })
        
        cleaning_up = {}
        final_links = []
        print(results)
        for result in results:
            print(result)
            temp_dict = {}
            if result["type"] == "Cross-reference":
                ref_no = result['target_text'].strip().split(' ')[1]
                ref_name = result['ref_text']
                ref_name = re.sub(r'[\u200e\u200f\u202a\u202b\u202c\u202d\u202e]', '', ref_name)
                if cleaning_up.get(f'{ref_no} {ref_name}', None):
                    cleaning_up[f'{ref_no} {ref_name}'].add(result["page_number"])
                else:
                    cleaning_up[f'{ref_no} {ref_name}'] = set([result["page_number"]])
                temp_dict["reference"] = ref_no
                temp_dict["reference_text"] = ref_name
                temp_dict["page_number"] = result["page_number"]
                final_links.append(temp_dict)
            else:
                if "Internal" in result['target']:
                    ref_no = result['target'].strip()
                    ref_no_m = result['target'].replace('Internal:', '').strip()
                    ref_name = result['link_text']
                    if cleaning_up.get(f'{ref_no} {ref_name}', None):
                        cleaning_up[f'{ref_no} {ref_name}'].add(result["page_number"])
                    else:
                        cleaning_up[f'{ref_no} {ref_name}'] = set([result["page_number"]])
                    temp_dict["reference"] = ref_no_m
                    temp_dict["reference_text"] = ref_name
                    temp_dict["page_number"] = result["page_number"]
                    final_links.append(temp_dict)

            print(temp_dict)
            print('***********************************************************************************')
        print(final_links)
        total_pages = doc.ComputeStatistics(2)
        headings = []
        for page_num in range(1, total_pages + 1):
                    page_start = doc.GoTo(What=1, Which=1, Count=page_num).Start  # 1 is wdGoToPage
                    page_end = doc.GoTo(What=1, Which=1, Count=page_num + 1).Start if page_num < total_pages else doc.Content.End
                    
                    # Create range object for current page
                    page_range = doc.Range(page_start, page_end)
            # Process each paragraph in the page
                    for para in page_range.Paragraphs:
                        if para.Range.Style and (('Heading' in para.Range.Style.NameLocal or 'Header' in para.Range.Style.NameLocal) and 'Table' not in para.Range.Style.NameLocal):
                            print(para.Range.Text)
                            # if para.Range.Text.strip():
                            name = para.Range.Text.strip()
                            name = re.sub(r'[\x00-\x1F\x7F\uF000-\uFFFF]', '', name)
                            number = None
                            if para.Range.ListFormat.ListType > 0:
                                number = para.Range.ListFormat.ListString.strip()
                                number =  re.sub(r'[\x00-\x1F\x7F\uF000-\uFFFF]', '', number)
                            headings.append((name, number, page_num))
                            print((name, number, page_num))
        heading_numbers_new = []
        sset = set()
        for ele in headings:
            if (ele[0], ele[1]) not in sset:
                heading_numbers_new.append(ele)
                sset.add((ele[0], ele[1]))
        headings = heading_numbers_new
        print(headings)
        print(cleaning_up)
        return cleaning_up, headings, final_links
    except Exception as e:
        logger.error(str(f'Encountered the following error while extracting links - {e}')+' [extract_links_and_references_pages] [scripts\check_doc_names.py:261]')
        raise Exception(str(f'Encountered the following error while extracting links - {e}'))
    finally:
        try:
            if doc:
                doc.Close(SaveChanges=0)
                del doc
        except Exception as close_err:
                logger.warning(f"Error closing document: {close_err}")

        try:
            if word:
                word.Quit()
                del word
        except Exception as quit_err:
            logger.warning(f"Error quitting Word: {quit_err}")

        pythoncom.CoUninitialize()
    
    