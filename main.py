from fastapi import FastAPI, HTTPException, File, UploadFile, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import os
from dotenv import load_dotenv
from supabase_client import supabase
from services.ocr_service import OCRService
from services.analysis_service import AnalysisService
import json
import re

load_dotenv()

app = FastAPI()

# Get allowed origins from environment variable or use default
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8080").split(",")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify the API key from the Authorization header"""
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="API key not configured")
    
    if credentials.credentials != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return credentials

# Initialize services
ocr_service = OCRService()
analysis_service = AnalysisService()

# Pydantic models
class ThesisBase(BaseModel):
    title: str
    content: str

class ThesisCreate(ThesisBase):
    pass

class Thesis(ThesisBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Function to sanitize text for database
def sanitize_for_db(text):
    if text is None:
        return None
    
    if isinstance(text, str):
        # Remove null bytes and other control characters
        return re.sub(r'[\x00-\x1F\x7F]', '', text)
    elif isinstance(text, dict):
        # Recursively sanitize dictionary values
        return {k: sanitize_for_db(v) for k, v in text.items()}
    elif isinstance(text, list):
        # Recursively sanitize list items
        return [sanitize_for_db(item) for item in text]
    else:
        # Return other types as is
        return text

# Function to prepare data for Supabase
def prepare_for_supabase(data):
    # First sanitize all text
    sanitized = sanitize_for_db(data)
    
    # Ensure JSON fields are properly formatted
    if isinstance(sanitized, dict):
        # For each field that should be JSON, make sure it's a valid JSON string
        for key in sanitized:
            if isinstance(sanitized[key], (dict, list)):
                try:
                    # Test if it can be JSON serialized
                    json.dumps(sanitized[key])
                except (TypeError, ValueError):
                    # If it can't be serialized, convert to string
                    sanitized[key] = str(sanitized[key])
    
    return sanitized

# Routes
@app.get("/")
async def root():
    return {"message": "Thesis API is running"}

@app.get("/api/theses/", response_model=List[Thesis])
async def get_theses():
    try:
        response = supabase.table('theses').select('*').execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/theses/{thesis_id}", response_model=Thesis)
async def get_thesis(thesis_id: str):
    try:
        response = supabase.table('theses').select('*').eq('id', thesis_id).single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Thesis not found")
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/theses/", response_model=Thesis)
async def create_thesis(thesis: ThesisCreate):
    try:
        thesis_data = {
            'id': str(uuid.uuid4()),
            'title': thesis.title,
            'content': thesis.content,
            'user_id': 'test-user',  # TODO: Implement proper user authentication
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        response = supabase.table('theses').insert(thesis_data).execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/theses/{thesis_id}", response_model=Thesis)
async def update_thesis(thesis_id: str, thesis: ThesisBase):
    try:
        thesis_data = {
            'title': thesis.title,
            'content': thesis.content,
            'updated_at': datetime.utcnow().isoformat()
        }
        response = supabase.table('theses').update(thesis_data).eq('id', thesis_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Thesis not found")
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/theses/{thesis_id}")
async def delete_thesis(thesis_id: str):
    try:
        response = supabase.table('theses').delete().eq('id', thesis_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Thesis not found")
        return {"message": "Thesis deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/papers/analyze")
async def analyze_paper(
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    if not file.filename.endswith(('.jpg', '.jpeg', '.png', '.pdf')):
        raise HTTPException(status_code=400, detail="Unsupported file format")

    try:
        # 1. Read file content
        content = await file.read()
        
        # 2. Extract text using OCR service
        extracted_text = await ocr_service.extract_text(content, file.content_type)
        # Sanitize extracted text right away
        extracted_text = sanitize_for_db(extracted_text)
        
        # 3. Run comprehensive analysis using OpenAI
        paper_analysis = await analysis_service.analyze_paper(extracted_text)
        citation_analysis = await analysis_service.analyze_citations(extracted_text)
        gap_analysis = await analysis_service.analyze_research_gaps(extracted_text)
        
        # 4. Generate a unique ID for the paper
        paper_id = str(uuid.uuid4())
        
        # 5. Prepare data for database
        now = datetime.now().isoformat()
        
        # Store full analysis data in the papers table
        try:
            basic_info = paper_analysis.get("basic_info", {})
            analysis_info = paper_analysis.get("analysis", {})
            
            # Prepare full paper data with all necessary fields
            paper_data = {
                "id": paper_id,
                "title": basic_info.get("title", "Untitled Paper"),
                "authors": basic_info.get("authors", []),
                "year_of_publication": basic_info.get("year_of_publication", "Unknown"),
                "paper_type": basic_info.get("type", "Unknown"),
                "relevance_score": analysis_info.get("relevance_score", 5),
                "file_url": f"local://{file.filename}",
                "paper_analysis": paper_analysis,
                "citation_analysis": citation_analysis,
                "gap_analysis": gap_analysis,
                "created_at": now,
                "updated_at": now,
                "extracted_text": extracted_text[:5000] if extracted_text else "",  # Store partial text as reference
                "filename": file.filename
            }
            
            # Sanitize and prepare data for Supabase
            safe_paper_data = prepare_for_supabase(paper_data)
            
            # Insert paper data into the papers table only
            response = supabase.table('papers').insert(safe_paper_data).execute()
            
            print(f"Paper saved to database with ID: {paper_id}")
            
        except Exception as db_error:
            print(f"Error saving to database: {str(db_error)}")
            # Continue even if database save fails
        
        # 6. Return the analysis results
        return {
            "message": "Paper analyzed successfully",
            "paper_id": paper_id,
            "file_url": f"local://{file.filename}",
            "analysis": {
                "paper_analysis": paper_analysis,
                "citation_analysis": citation_analysis,
                "gap_analysis": gap_analysis
            }
        }
        
    except Exception as e:
        print(f"Error analyzing paper: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/papers/", response_model=List[Dict[str, Any]])
async def get_papers(credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)):
    """Get all analyzed papers with their summaries"""
    try:
        # Only select the metadata fields needed for listing
        response = supabase.table('papers').select(
            'id,title,authors,year_of_publication,paper_type,relevance_score,created_at,updated_at,filename'
        ).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/papers/{paper_id}", response_model=Dict[str, Any])
async def get_paper_details(
    paper_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    """Get detailed analysis of a specific paper"""
    try:
        response = supabase.table('papers').select('*').eq('id', paper_id).single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Paper not found")
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/papers/search/", response_model=List[Dict[str, Any]])
async def search_papers(
    query: str = None,
    year: int = None,
    type: str = None,
    min_relevance: int = None,
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    """Search papers with filters"""
    try:
        # Only select the metadata fields needed for listing
        query_builder = supabase.table('papers').select(
            'id,title,authors,year_of_publication,paper_type,relevance_score,created_at,updated_at,filename'
        )
        
        if query:
            query_builder = query_builder.or_(f"title.ilike.%{query}%,authors.ilike.%{query}%")
        if year:
            query_builder = query_builder.eq('year_of_publication', str(year))
        if type:
            query_builder = query_builder.eq('paper_type', type)
        if min_relevance:
            query_builder = query_builder.gte('relevance_score', min_relevance)
            
        response = query_builder.execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/papers/{paper_id}", response_model=Dict[str, Any])
async def update_paper_analysis(
    paper_id: str,
    update_data: Dict[str, Any],
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    """Update an existing paper analysis"""
    try:
        # Check if paper exists
        check_response = supabase.table('papers').select('id').eq('id', paper_id).single().execute()
        if not check_response.data:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        # Update timestamp
        update_data["updated_at"] = datetime.now().isoformat()
        
        # If paper_analysis is provided, ensure we update the metadata fields too
        if "paper_analysis" in update_data:
            paper_analysis = update_data["paper_analysis"]
            basic_info = paper_analysis.get("basic_info", {})
            analysis_info = paper_analysis.get("analysis", {})
            
            # Update core metadata fields
            if "title" in basic_info:
                update_data["title"] = basic_info["title"]
            if "authors" in basic_info:
                update_data["authors"] = basic_info["authors"]
            if "year_of_publication" in basic_info:
                update_data["year_of_publication"] = basic_info["year_of_publication"]
            if "type" in basic_info:
                update_data["paper_type"] = basic_info["type"]
            if "relevance_score" in analysis_info:
                update_data["relevance_score"] = analysis_info["relevance_score"]
        
        # Sanitize and prepare data for Supabase
        safe_update_data = prepare_for_supabase(update_data)
        
        # Update paper in the papers table
        response = supabase.table('papers').update(safe_update_data).eq('id', paper_id).execute()
        
        return {
            "message": "Paper analysis updated successfully",
            "paper_id": paper_id,
            "updated_data": response.data[0] if response.data else {}
        }
    except Exception as e:
        print(f"Error updating paper analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/papers/{paper_id}")
async def delete_paper(
    paper_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    """Delete a paper analysis"""
    try:
        # Check if paper exists
        check_response = supabase.table('papers').select('id').eq('id', paper_id).single().execute()
        if not check_response.data:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        # Delete from papers table
        papers_response = supabase.table('papers').delete().eq('id', paper_id).execute()
        
        return {"message": "Paper deleted successfully"}
    except Exception as e:
        print(f"Error deleting paper: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/papers/batch-analyze")
async def batch_analyze_papers(
    files: List[UploadFile] = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    """Batch analyze multiple papers"""
    results = []
    errors = []
    
    if len(files) > 10:
        raise HTTPException(
            status_code=400, 
            detail="Maximum 10 files allowed for batch processing"
        )
    
    for file in files:
        try:
            # Validate file format
            if not file.filename.endswith(('.jpg', '.jpeg', '.png', '.pdf')):
                errors.append({
                    "filename": file.filename,
                    "error": "Unsupported file format"
                })
                continue
                
            # 1. Read file content
            content = await file.read()
            
            # 2. Extract text
            extracted_text = await ocr_service.extract_text(content, file.content_type)
            # Sanitize extracted text right away
            extracted_text = sanitize_for_db(extracted_text)
            
            # 3. Run analysis
            paper_analysis = await analysis_service.analyze_paper(extracted_text)
            citation_analysis = await analysis_service.analyze_citations(extracted_text)
            gap_analysis = await analysis_service.analyze_research_gaps(extracted_text)
            
            # 4. Generate ID and prepare data
            paper_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # 5. Save to database
            try:
                basic_info = paper_analysis.get("basic_info", {})
                analysis_info = paper_analysis.get("analysis", {})
                
                # Prepare full paper data with all necessary fields
                paper_data = {
                    "id": paper_id,
                    "title": basic_info.get("title", "Untitled Paper"),
                    "authors": basic_info.get("authors", []),
                    "year_of_publication": basic_info.get("year_of_publication", "Unknown"),
                    "paper_type": basic_info.get("type", "Unknown"),
                    "relevance_score": analysis_info.get("relevance_score", 5),
                    "file_url": f"local://{file.filename}",
                    "paper_analysis": paper_analysis,
                    "citation_analysis": citation_analysis,
                    "gap_analysis": gap_analysis,
                    "created_at": now,
                    "updated_at": now,
                    "extracted_text": extracted_text[:5000] if extracted_text else "",
                    "filename": file.filename
                }
                
                # Sanitize and prepare data for Supabase
                safe_paper_data = prepare_for_supabase(paper_data)
                
                # Insert into papers table only
                supabase.table('papers').insert(safe_paper_data).execute()
                
            except Exception as db_error:
                print(f"Database error for {file.filename}: {str(db_error)}")
                # Continue processing even if database save fails
            
            # 6. Add to results
            results.append({
                "filename": file.filename,
                "paper_id": paper_id,
                "title": basic_info.get("title", "Untitled Paper"),
                "success": True
            })
            
        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return {
        "message": f"Processed {len(results)} papers successfully, {len(errors)} failures",
        "results": results,
        "errors": errors
    }

@app.get("/api/papers/{paper_id}/similar", response_model=List[Dict[str, Any]])
async def get_similar_papers(
    paper_id: str,
    limit: int = 5,
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    """Get papers similar to the given paper"""
    try:
        # First get the source paper
        paper_response = supabase.table('papers').select('*').eq('id', paper_id).single().execute()
        if not paper_response.data:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        source_paper = paper_response.data
        
        # Extract key characteristics for comparison
        paper_analysis = source_paper.get("paper_analysis", {})
        basic_info = paper_analysis.get("basic_info", {})
        analysis_info = paper_analysis.get("analysis", {})
        
        # Get keywords for matching (from methods, findings, etc.)
        keywords = []
        
        # Add methods as keywords
        if "methods" in analysis_info:
            methods = analysis_info["methods"]
            if "methodology_type" in methods:
                keywords.append(methods["methodology_type"])
            if "specific_methods" in methods and isinstance(methods["specific_methods"], list):
                keywords.extend(methods["specific_methods"])
        
        # Add main findings as keywords
        if "main_findings" in analysis_info and isinstance(analysis_info["main_findings"], list):
            keywords.extend(analysis_info["main_findings"])
        
        # Add paper type as keyword
        if "type" in basic_info:
            keywords.append(basic_info["type"])
        
        # Get all papers (only metadata fields for comparison)
        all_papers_response = supabase.table('papers').select(
            'id,title,authors,year_of_publication,paper_type,relevance_score,created_at,updated_at,filename'
        ).neq('id', paper_id).execute()
        
        if not all_papers_response.data:
            return []
        
        all_papers = all_papers_response.data
        similar_papers = []
        
        # Simple similarity scoring - can be improved later
        for paper in all_papers:
            score = 0
            
            # Match by paper type
            if paper.get("paper_type") == basic_info.get("type"):
                score += 2
            
            # Match by year (within 5 years)
            source_year = basic_info.get("year_of_publication", "Unknown")
            paper_year = paper.get("year_of_publication", "Unknown")
            
            try:
                if source_year != "Unknown" and paper_year != "Unknown":
                    source_year_int = int(source_year)
                    paper_year_int = int(paper_year)
                    if abs(source_year_int - paper_year_int) <= 5:
                        score += 1
            except ValueError:
                pass
            
            # For now, use these simple metrics
            # Add paper with similarity score
            similar_papers.append({
                **paper,
                "similarity_score": score
            })
        
        # Sort by similarity score and take top 'limit'
        similar_papers.sort(key=lambda p: p["similarity_score"], reverse=True)
        return similar_papers[:limit]
    
    except Exception as e:
        print(f"Error finding similar papers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 