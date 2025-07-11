# 📄 OCR Text Enhancement Tool

A powerful Streamlit web application that enhances OCR-extracted text from documents stored in AWS S3. This tool uses AWS Textract for OCR and AI-powered text enhancement to fix spelling mistakes, correct OCR errors, and improve text readability.

## ✨ Features

### 🔍 **Document Management**
- Browse documents stored in AWS S3
- Support for PDF and image files (JPG, PNG)
- Real-time file listing with metadata
- Document preview with high-quality rendering

### 🧠 **AI-Powered Text Enhancement**
- OCR text extraction using AWS Textract
- AI-powered spelling and grammar correction
- OCR error detection and fixing
- Text formatting improvements
- Low-temperature AI processing for accuracy

### 📊 **Detailed Analysis**
- Side-by-side original vs enhanced text comparison
- Detailed change tracking with categories
- Color-coded correction types
- Comprehensive enhancement summary
- Original text preservation for reference

### 💾 **Export & Download**
- Download enhanced text as .txt files
- Formatted output for easy reading
- Batch processing capabilities

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- AWS account with configured credentials
- S3 bucket with documents
- Lambda function for text enhancement (API endpoint)

### Installation

1. **Clone or download the project:**
```bash
mkdir ocr-enhancement-tool
cd ocr-enhancement-tool
```

2. **Create the required files:**
   - Save the application code as `app.py`
   - Save the dependencies as `requirements.txt`

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure AWS credentials:**

Choose one of the following methods:

**Option A: AWS CLI**
```bash
aws configure
```

**Option B: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=your_access_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_access_key
export AWS_DEFAULT_REGION=us-east-1
```

**Option C: IAM Role (for EC2 instances)**
- Attach an IAM role with S3 permissions to your EC2 instance

### Configuration

Edit the configuration variables in `app.py`:

```python
# Configuration
S3_BUCKET = "your-s3-bucket-name"           # Your S3 bucket
S3_FOLDER = "pytextract"                    # Folder containing documents
LAMBDA_API_URL = "your-lambda-api-endpoint" # Your enhancement API endpoint
```

### Run the Application

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

## 🔧 AWS Setup

### Required AWS Services

1. **S3 Bucket**: Store your documents
2. **AWS Textract**: OCR processing
3. **AWS Lambda**: Text enhancement API
4. **AWS Bedrock**: AI model for text enhancement

### IAM Permissions

Your AWS user/role needs the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetObject"
            ],
            "Resource": [
                "arn:aws:s3:::your-bucket-name",
                "arn:aws:s3:::your-bucket-name/*"
            ]
        }
    ]
}
```

### S3 Bucket Structure

```
your-s3-bucket/
└── pytextract/
    ├── document1.pdf
    ├── handwritten-note.jpg
    ├── scan.png
    └── ...
```

## 🖥️ User Interface

### Sidebar - Document Browser
- **File List**: All documents in your S3 folder
- **File Details**: Name, size, modification date
- **Refresh Button**: Update file list
- **Enhance Button**: Process selected document

### Main Area - Split View
**Left Panel - Original Document**
- PDF preview (first page)
- Image display for JPG/PNG files
- High-quality rendering

**Right Panel - Enhanced Text**
- AI-enhanced text output
- Formatted for readability
- Download button for saving

### Bottom Section - Analysis
**Left Panel - Changes Made**
- Detailed list of corrections
- Original vs corrected text
- Color-coded change types:
  - 🟢 Spelling corrections
  - 🟡 OCR error fixes
  - 🔵 Formatting improvements

**Right Panel - Summary**
- Overall enhancement summary
- Original OCR text (expandable)
- Processing statistics

## 📱 Usage Guide

### Step 1: Select Document
1. View available documents in the sidebar
2. Click on a document to select it
3. Review file details (size, date)

### Step 2: Enhance Text
1. Click the "✨ Enhance Text" button
2. Wait for processing (progress indicator shown)
3. View results in the main area

### Step 3: Review Results
1. Compare original document (left) with enhanced text (right)
2. Review detailed changes in the bottom section
3. Read the enhancement summary

### Step 4: Download Results
1. Click "💾 Download Enhanced Text"
2. Save the improved text as a .txt file
3. Use the enhanced text in your workflow

## 🛠️ Technical Details

### Dependencies

- **streamlit**: Web application framework
- **boto3**: AWS SDK for Python
- **requests**: HTTP library for API calls
- **Pillow**: Image processing
- **PyMuPDF**: PDF handling and rendering

### File Support

| Format | Preview | OCR Support | Notes |
|--------|---------|-------------|-------|
| PDF | ✅ First page | ✅ | Up to 10MB |
| JPG | ✅ Full image | ✅ | Recommended |
| PNG | ✅ Full image | ✅ | Recommended |
| JPEG | ✅ Full image | ✅ | Recommended |

### API Integration

The application integrates with a Lambda function that:
1. Receives S3 file location
2. Processes document with AWS Textract
3. Enhances text using AI (AWS Bedrock)
4. Returns structured results

**API Request:**
```json
{
    "bucket": "your-bucket-name",
    "key": "pytextract/document.pdf"
}
```

**API Response:**
```json
{
    "original_text": "Original OCR text...",
    "enhanced_text": "Enhanced and corrected text...",
    "changes_made": [
        {
            "original": "teh",
            "corrected": "the",
            "type": "spelling"
        }
    ],
    "summary": "Fixed 3 spelling errors and 2 OCR mistakes"
}
```

## 🔍 Troubleshooting

### Common Issues

**"No files found in pytextract folder"**
- ✅ Check S3 bucket name in configuration
- ✅ Verify folder path exists
- ✅ Ensure AWS credentials have S3 read permissions

**"Error listing S3 files"**
- ✅ Verify AWS credentials are configured
- ✅ Check IAM permissions for S3 access
- ✅ Ensure bucket exists and is accessible

**"API Error" when enhancing**
- ✅ Verify Lambda API URL is correct
- ✅ Check Lambda function is deployed and running
- ✅ Ensure API Gateway is properly configured

**"PDF display error"**
- ✅ Install PyMuPDF: `pip install PyMuPDF`
- ✅ Some complex PDFs may not render properly
- ✅ Try converting PDF to image format

**"Request timed out"**
- ✅ Document may be too large (>10MB limit)
- ✅ Complex documents take longer to process
- ✅ Check Lambda function timeout settings

### Debug Mode

Enable debug information by adding to the sidebar:

```python
if st.checkbox("Debug Mode"):
    st.write("Session State:", st.session_state)
    st.write("Selected File:", st.session_state.selected_file)
```

## 📁 Project Structure

```
ocr-enhancement-tool/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── README.md             # This documentation
└── .gitignore            # Git ignore file (optional)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License. See LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review AWS service limits and quotas
3. Verify all configuration settings
4. Test with a simple document first

## 🔮 Future Enhancements

- [ ] Batch processing multiple documents
- [ ] Support for additional file formats
- [ ] Advanced text formatting options
- [ ] Integration with more AI models
- [ ] Export to various formats (Word, PDF)
- [ ] User authentication and access control
- [ ] Document history and versioning

---

**Made with ❤️ using Streamlit and AWS services**