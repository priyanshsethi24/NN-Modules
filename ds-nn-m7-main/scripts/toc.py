from common.logs import logger
import re

def clean_text(text):
    text = re.sub(r'^[\d.]+', '', text)
    text = re.sub(r'\d+$', '', text)
    return text.strip()

def toc_errors(data,page_nums,llist):
    try:
        errors = []  
        bookmarks = data.get("bookmarks", [])
        logger.info(str(f'TOC bookmarks - {bookmarks}')+'[methodName] [scripts\toc.py:14]')

        for bookmark in bookmarks:
            bookmark_name = bookmark.get("bookmark_name", "")
            
            if not bookmark_name.startswith("_Toc"):
                continue

            document_text = bookmark.get("bookmark_text", "").strip() 
            referenced_text = bookmark.get("destination_text","").strip()
            pages = list(page_nums.get(f'Internal: {bookmark_name} ', []))
            print(bookmark_name, pages)
            page_number = pages[0] if pages else None
             
            # Fetch all matching entries for bookmark_name
            matching_entries = [val for key, val in llist if key == bookmark_name]

            # If there are multiple entries, prioritize the one with letters
            if matching_entries:
                for entry in matching_entries:
                    if any(c.isalpha() for c in entry):  # Check if entry contains alphabets
                        document_text = clean_text(entry)
                        break  
            
            normalized_doc_text = re.sub(r'\s+', '', document_text)
            normalized_ref_text = re.sub(r'\s+', '', referenced_text)
            has_error = normalized_doc_text != normalized_ref_text
            
            if page_number is not None:
                if document_text:
                    errors.append({
                        "document_text": document_text,
                        "referenced_text": referenced_text if len(referenced_text) < 200 else "Invalid link format",
                        "has_error": has_error,
                        "page": page_number
                    })
        print("TOC errors list", errors)
        return errors
        
    except Exception as e:
        logger.error('Encountered an error while extracting TOC errors: %s', str(e))
        raise Exception(str(e))
