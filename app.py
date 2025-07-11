import streamlit as st
import boto3
import requests
import json
from PIL import Image
import fitz  # PyMuPDF for PDF handling
import io
from botocore.exceptions import ClientError
import base64

# Page config
st.set_page_config(
    page_title="OCR Text Enhancement",
    page_icon="📄",
    layout="wide"
)

# Configuration idealy these will be moved in production 
S3_BUCKET = "nikhil-personal-test"
S3_FOLDER = "pytextract"
LAMBDA_API_URL = "https://notorginal.execute-api.us-east-1.amazonaws.com/prod/pleasechangetheapi"

# Initialize session state
if 'enhanced_data' not in st.session_state:
    st.session_state.enhanced_data = None
if 'selected_file' not in st.session_state:
    st.session_state.selected_file = None

@st.cache_resource
def get_s3_client():
    """Initialize S3 client"""
    return boto3.client('s3')

@st.cache_data(ttl=300)
def list_s3_files():
    """List files in S3 pytextract folder"""
    try:
        s3_client = get_s3_client()
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=f"{S3_FOLDER}/"
        )
        
        files = []
        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                if key != f"{S3_FOLDER}/":  # Skip folder itself
                    files.append({
                        'key': key,
                        'name': key.split('/')[-1],
                        'size': obj['Size'],
                        'modified': obj['LastModified']
                    })
        return files
    except Exception as e:
        st.error(f"Error listing S3 files: {str(e)}")
        return []

def download_s3_file(key):
    """Download file from S3"""
    try:
        s3_client = get_s3_client()
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        return response['Body'].read()
    except Exception as e:
        st.error(f"Error downloading file: {str(e)}")
        return None

def call_enhancement_api(bucket, key):
    """Call the Lambda API for text enhancement"""
    try:
        payload = {
            "bucket": bucket,
            "key": key
        }
        
        with st.spinner("Processing document..."):
            response = requests.post(
                LAMBDA_API_URL,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=60
            )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        st.error("Request timed out. The document might be too large or complex.")
        return None
    except Exception as e:
        st.error(f"Error calling API: {str(e)}")
        return None

def display_pdf(file_data):
    """Display PDF using PyMuPDF"""
    try:
        pdf_document = fitz.open(stream=file_data, filetype="pdf")
        
        # Convert first page to image for display
        page = pdf_document[0]
        mat = fitz.Matrix(2, 2)  # Scale factor for better quality
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        pdf_document.close()
        
        image = Image.open(io.BytesIO(img_data))
        return image
        
    except Exception as e:
        st.error(f"Error displaying PDF: {str(e)}")
        return None

def display_image(file_data):
    """Display image file"""
    try:
        image = Image.open(io.BytesIO(file_data))
        return image
    except Exception as e:
        st.error(f"Error displaying image: {str(e)}")
        return None

def format_enhanced_text(text):
    """Format enhanced text for better display"""
    if not text:
        return "No text detected"
    
    # Split by lines and format
    lines = text.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if line:
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)

def display_changes(changes):
    """Display changes in a formatted way"""
    if not changes:
        st.info("No changes were made to the text")
        return
    
    st.subheader("Changes Made:")
    
    for i, change in enumerate(changes, 1):
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            st.text(f"Original: {change.get('original', 'N/A')}")
        
        with col2:
            st.text(f"Corrected: {change.get('corrected', 'N/A')}")
        
        with col3:
            change_type = change.get('type', 'unknown')
            if change_type == 'spelling':
                st.success("Spelling")
            elif change_type == 'ocr_error':
                st.warning("OCR Error")
            elif change_type == 'formatting':
                st.info("Formatting")
            else:
                st.text(change_type.title())
        
        if i < len(changes):
            st.divider()

# Main app
def main():
    st.title("📄 OCR Text Enhancement Tool")
    st.markdown("---")
    
    # Sidebar for file selection
    with st.sidebar:
        st.header("📁 Documents")
        
        if st.button("🔄 Refresh Files"):
            st.cache_data.clear()
        
        files = list_s3_files()
        
        if not files:
            st.warning("No files found in pytextract folder")
            return
        
        # File selection
        file_names = [f"{f['name']} ({f['size']} bytes)" for f in files]
        selected_idx = st.selectbox(
            "Select a document:",
            range(len(file_names)),
            format_func=lambda x: file_names[x],
            index=0 if st.session_state.selected_file is None else 
                  next((i for i, f in enumerate(files) if f['key'] == st.session_state.selected_file), 0)
        )
        
        selected_file = files[selected_idx]
        st.session_state.selected_file = selected_file['key']
        
        # File info
        st.markdown("**File Details:**")
        st.text(f"Name: {selected_file['name']}")
        st.text(f"Size: {selected_file['size']} bytes")
        st.text(f"Modified: {selected_file['modified'].strftime('%Y-%m-%d %H:%M')}")
        
        # Enhance button
        if st.button("✨ Enhance Text", type="primary", use_container_width=True):
            result = call_enhancement_api(S3_BUCKET, selected_file['key'])
            if result:
                st.session_state.enhanced_data = result
                st.success("Enhancement completed!")
    
    # Main content area
    if st.session_state.selected_file:
        # Download and display the selected file
        file_data = download_s3_file(st.session_state.selected_file)
        
        if file_data:
            col1, col2 = st.columns(2)
            
            # Left column - Original document
            with col1:
                st.subheader("📄 Original Document")
                
                file_name = st.session_state.selected_file.lower()
                
                if file_name.endswith('.pdf'):
                    image = display_pdf(file_data)
                    if image:
                        st.image(image, use_column_width=True)
                
                elif file_name.endswith(('.jpg', '.jpeg', '.png')):
                    image = display_image(file_data)
                    if image:
                        st.image(image, use_column_width=True)
                
                else:
                    st.warning("Unsupported file format for preview")
            
            # Right column - Enhanced text
            with col2:
                st.subheader("✨ Enhanced Text")
                
                if st.session_state.enhanced_data:
                    enhanced_text = st.session_state.enhanced_data.get('enhanced_text', '')
                    formatted_text = format_enhanced_text(enhanced_text)
                    
                    # Display enhanced text in a text area
                    st.text_area(
                        "Enhanced Text:",
                        value=formatted_text,
                        height=400,
                        disabled=True
                    )
                    
                    # Download button for enhanced text
                    if formatted_text:
                        st.download_button(
                            label="💾 Download Enhanced Text",
                            data=formatted_text,
                            file_name=f"enhanced_{selected_file['name']}.txt",
                            mime="text/plain"
                        )
                else:
                    st.info("Click 'Enhance Text' to process the document")
            
            # Bottom section - Changes and summary
            if st.session_state.enhanced_data:
                st.markdown("---")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    display_changes(st.session_state.enhanced_data.get('changes_made', []))
                
                with col2:
                    st.subheader("📋 Summary")
                    summary = st.session_state.enhanced_data.get('summary', 'No summary available')
                    st.success(summary)
                    
                    # Show original text for comparison
                    with st.expander("👁️ View Original OCR Text"):
                        original_text = st.session_state.enhanced_data.get('original_text', '')
                        st.text_area(
                            "Original OCR Text:",
                            value=original_text,
                            height=200,
                            disabled=True
                        )
    
    else:
        st.info("Please select a document from the sidebar to get started.")

# Custom CSS for better styling
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
    }
    
    .stTextArea > div > div > textarea {
        font-family: 'Courier New', monospace;
    }
    
    .success-box {
        padding: 10px;
        border-radius: 5px;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    
    .warning-box {
        padding: 10px;
        border-radius: 5px;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
    }
</style>
""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()