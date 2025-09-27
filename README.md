# SortSense ♻️ — AI Waste Sorter

A smart waste management application that uses AI to classify waste items from photos and parse waste invoices from PDFs, helping organizations track and optimize their waste diversion efforts.

## 🌟 Features

- **AI-Powered Image Classification**: Upload photos of waste items and get instant classification (recycle, compost, landfill)
- **PDF Invoice Processing**: Upload waste management invoices to automatically extract and categorize waste data
- **Real-time KPIs**: Track recycling, composting, and landfill diversion rates
- **Smart Tips**: Get helpful sorting tips for each classified item
- **Modern UI**: Clean, responsive interface built with Next.js and TypeScript

## 🏗️ Architecture

```
sortsense/
├── frontend/sortsense-ui/     # Next.js React frontend
├── backend/                   # FastAPI Python backend
└── infra/                     # AWS infrastructure (SAM templates)
```

### Tech Stack

**Frontend:**
- Next.js 15 with TypeScript
- React with modern hooks
- Tailwind CSS for styling

**Backend:**
- FastAPI (Python)
- AWS Bedrock for AI vision
- AWS Textract for PDF processing
- Snowflake for data warehousing
- AWS S3 for file storage

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- Git

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd sortsense
   ```

2. **Start the backend server**
   ```bash
   cd backend
   pip install -r requirements.txt
   python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Start the frontend development server**
   ```bash
   cd frontend/sortsense-ui
   npm install
   npm run dev
   ```

4. **Open your browser**
   Navigate to [http://localhost:3000](http://localhost:3000)

## 📱 How to Use

### Upload Waste Photos
1. Click "Choose file" under "Upload trash photo"
2. Select an image file (JPG, PNG, etc.)
3. Wait for AI classification
4. View detected items with sorting recommendations

### Upload Waste Invoices
1. Click "Choose file" under "Upload waste invoice (PDF)"
2. Select a PDF invoice file
3. View parsed waste data and costs

### View KPIs
- See real-time waste diversion metrics
- Click "Refresh KPIs" to update data
- Click "Reset KPIs" to start fresh

## 🔧 Configuration

### Environment Variables

The backend uses the following environment variables (configured in `template.yaml` for AWS deployment):

```bash
S3_BUCKET=your-s3-bucket-name
AWS_REGION=us-west-2
LLAMA_VISION_MODEL=meta.llama3-2-11b-vision-instruct-v1:0
SNOWFLAKE_USER=your-snowflake-user
SNOWFLAKE_PASSWORD=your-snowflake-password
SNOWFLAKE_ACCOUNT=your-snowflake-account
SNOWFLAKE_WAREHOUSE=DEFAULT_WH
SNOWFLAKE_DATABASE=DEFAULT_DATABASE
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_ROLE=ATTENDEE_ROLE
WRITER_API_KEY=your-writer-api-key
WRITER_MODEL=palmyra-x5
```

### Local Development Mode

For local development, the application uses mock data instead of requiring AWS services:

- **Image Classification**: Returns mock items (plastic bottle, aluminum can, pizza box)
- **PDF Processing**: Returns mock invoice data
- **KPIs**: Tracks data in memory (resets on server restart)

## 🚀 Deployment

### AWS Deployment (Production)

1. **Install AWS SAM CLI**
   ```bash
   pip install aws-sam-cli
   ```

2. **Configure AWS credentials**
   ```bash
   aws configure
   ```

3. **Deploy the backend**
   ```bash
   cd backend
   sam build
   sam deploy --guided
   ```

4. **Update frontend API URL**
   Update the `API` constant in `frontend/sortsense-ui/app/page.tsx` with your deployed API Gateway URL.

5. **Deploy frontend**
   Deploy to Vercel, Netlify, or your preferred hosting platform.

## 📊 Data Flow

1. **Image Upload** → S3 Storage → Bedrock Vision AI → Classification → Snowflake
2. **PDF Upload** → S3 Storage → Textract → Invoice Parsing → Snowflake
3. **KPI Calculation** → Snowflake Query → Real-time Metrics Display

## 🛠️ Development

### Backend API Endpoints

- `POST /upload-image` - Upload and classify waste photos
- `POST /upload-invoice` - Upload and parse waste invoices
- `GET /kpis` - Get current waste diversion metrics
- `POST /reset-kpis` - Reset KPIs to zero (development only)

### Database Schema

**WASTE_EVENTS Table:**
- EVENT_ID, TS, SOURCE, LABEL, ROUTE, CONFIDENCE, EST_WEIGHT_KG, METADATA

**INVOICE_LINES Table:**
- INVOICE_ID, PERIOD, VENDOR, LINE_TYPE, WEIGHT_KG, COST_USD, TS

**VIEW_KPIS View:**
- recycle_kg, compost_kg, landfill_kg, diversion_rate

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- AWS Bedrock for AI vision capabilities
- AWS Textract for document processing
- Snowflake for data warehousing
- FastAPI for the backend framework
- Next.js for the frontend framework

## 📞 Support

For support, email support@sortsense.com or create an issue in this repository.

---

**SortSense** - Making waste management smarter, one upload at a time! ♻️
