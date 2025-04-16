from mistralai.client import MistralClient
from openai import OpenAI
import os
from typing import Dict, Any
import base64

class AnalysisService:
    def __init__(self):
        mistral_api_key = os.getenv("MISTRAL_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not mistral_api_key:
            raise ValueError("MISTRAL_API_KEY not set")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not set")
            
        self.mistral_client = MistralClient(api_key=mistral_api_key)
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.model = "mistral-large-latest"
        self.openai_model = "gpt-4o"

    async def extract_key_info(self, text: str) -> Dict[str, Any]:
        """Use Mistral to extract key information from text"""
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that extracts key information from academic texts."
            },
            {
                "role": "user",
                "content": f"""
                Please analyze this text and extract the following information in JSON format:
                - title: The main title or topic
                - abstract: A brief summary (max 200 words)
                - keywords: List of 5-10 key terms or concepts
                - main_points: List of 3-5 main arguments or findings
                
                Text to analyze: {text[:4000]}  # Limit text length for API
                """
            }
        ]
        
        response = self.mistral_client.chat.complete(
            model=self.model,
            messages=messages
        )
        return response.choices[0].message.content

    async def analyze_content(self, extracted_info: Dict[str, Any]) -> Dict[str, Any]:
        """Use OpenAI to perform deeper analysis"""
        prompt = f"""
        Analyze the following academic content and provide:
        1. Research methodology assessment
        2. Critical evaluation of arguments
        3. Potential gaps or limitations
        4. Future research directions
        5. Academic impact score (1-10)
        
        Content to analyze:
        {str(extracted_info)}
        """
        
        response = self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {"role": "system", "content": "You are an expert academic analyst."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content

    async def analyze_paper(self, text_content: str) -> Dict[str, Any]:
        """Comprehensive academic paper analysis using GPT-4o"""
        try:
            completion = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": """You are an expert academic paper analyzer. 
                    Analyze the paper and provide a detailed JSON response with the following structure:
                    {
                        "basic_info": {
                            "title": "full title of the paper",
                            "authors": ["list of all authors"],
                            "year_of_publication": "year (extract from text)",
                            "type": "type of paper (e.g., research article, review, case study)",
                            "link_to_article": "URL if mentioned in the text"
                        },
                        "analysis": {
                            "relevance_score": 1-10,
                            "relevance_explanation": "detailed explanation of relevance to field",
                            "main_findings": [
                                "list of key findings and conclusions"
                            ],
                            "methods": {
                                "methodology_type": "primary methodology used",
                                "specific_methods": ["list of specific methods used"],
                                "data_collection": "description of data collection process",
                                "analysis_techniques": ["list of analysis techniques"]
                            },
                            "gaps_and_limitations": {
                                "identified_gaps": ["list of research gaps"],
                                "limitations": ["list of study limitations"],
                                "methodology_limitations": ["specific limitations in methods"]
                            }
                        },
                        "quality_metrics": {
                            "methodology_score": 1-10,
                            "data_quality_score": 1-10,
                            "innovation_score": 1-10,
                            "impact_score": 1-10
                        },
                        "meta_info": {
                            "reviewer_initials": "extract or mark as N/A",
                            "review_date": "current date",
                            "additional_notes": ["any other important observations"]
                        }
                    }"""},
                    {"role": "user", "content": f"Analyze this academic paper and provide a detailed assessment. Extract all available information for each field. If any field cannot be determined from the text, mark it as 'Not specified in text':\n\n{text_content}"}
                ]
            )
            
            content = completion.choices[0].message.content
            print(f"Paper analysis raw response: {content}")
            
            # Try to parse the response as JSON
            import json
            try:
                # Check if the response is already JSON
                return json.loads(content)
            except json.JSONDecodeError:
                # If not, try to extract JSON from markdown or text
                if "```json" in content:
                    # Extract JSON from markdown code block
                    json_str = content.split("```json")[1].split("```")[0].strip()
                    return json.loads(json_str)
                else:
                    # Create a fallback structure
                    print("Could not parse JSON from paper analysis response")
                    return {
                        "basic_info": {
                            "title": "Analysis of document",
                            "authors": ["Not extracted"],
                            "year_of_publication": "Not extracted",
                            "type": "Not extracted",
                            "link_to_article": "Not found"
                        },
                        "analysis": {
                            "relevance_score": 5,
                            "relevance_explanation": "Relevance could not be determined",
                            "main_findings": ["Could not extract findings from text"],
                            "methods": {
                                "methodology_type": "Not specified",
                                "specific_methods": ["Not extracted"],
                                "data_collection": "Not specified",
                                "analysis_techniques": ["Not extracted"]
                            },
                            "gaps_and_limitations": {
                                "identified_gaps": ["Not extracted"],
                                "limitations": ["Not extracted"],
                                "methodology_limitations": ["Not extracted"]
                            }
                        },
                        "quality_metrics": {
                            "methodology_score": 5,
                            "data_quality_score": 5,
                            "innovation_score": 5,
                            "impact_score": 5
                        },
                        "meta_info": {
                            "reviewer_initials": "N/A",
                            "review_date": "Current",
                            "additional_notes": ["Analysis failed to produce structured output"]
                        }
                    }

        except Exception as e:
            print(f"OpenAI analysis error: {str(e)}")
            raise Exception(f"OpenAI analysis error: {str(e)}")

    async def analyze_citations(self, text_content: str) -> Dict[str, Any]:
        """Analyze citation quality and academic references"""
        try:
            completion = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": """Analyze the citations and references in this paper.
                    Provide a JSON response with:
                    {
                        "citation_metrics": {
                            "total_citations": number,
                            "unique_sources": number,
                            "year_range": "oldest to newest citation",
                            "most_cited_authors": ["list of frequently cited authors"]
                        },
                        "citation_quality": {
                            "recency": {
                                "score": 1-10,
                                "analysis": "assessment of citation dates",
                                "recent_citations": "number of citations from last 5 years"
                            },
                            "authority": {
                                "score": 1-10,
                                "key_references": ["most important references"],
                                "seminal_works": ["foundational papers cited"]
                            },
                            "diversity": {
                                "score": 1-10,
                                "source_types": ["distribution of source types"],
                                "field_coverage": "breadth of field coverage"
                            }
                        },
                        "recommendations": {
                            "missing_citations": ["suggested additional citations"],
                            "citation_improvements": ["ways to improve citation quality"],
                            "key_papers_to_add": ["specific papers to consider adding"]
                        }
                    }"""},
                    {"role": "user", "content": f"Analyze the citations in this paper:\n\n{text_content}"}
                ]
            )
            
            content = completion.choices[0].message.content
            print(f"Citation analysis raw response: {content}")
            
            # Try to parse the response as JSON
            import json
            try:
                # Check if the response is already JSON
                return json.loads(content)
            except json.JSONDecodeError:
                # If not, try to extract JSON from markdown or text
                if "```json" in content:
                    # Extract JSON from markdown code block
                    json_str = content.split("```json")[1].split("```")[0].strip()
                    return json.loads(json_str)
                else:
                    # Create a fallback structure
                    print("Could not parse JSON from citation analysis response")
                    return {
                        "citation_metrics": {
                            "total_citations": 0,
                            "unique_sources": 0,
                            "year_range": "Not determined",
                            "most_cited_authors": ["Not extracted"]
                        },
                        "citation_quality": {
                            "recency": {
                                "score": 5,
                                "analysis": "Citation dates could not be determined",
                                "recent_citations": 0
                            },
                            "authority": {
                                "score": 5,
                                "key_references": ["Not determined"],
                                "seminal_works": ["Not determined"]
                            },
                            "diversity": {
                                "score": 5,
                                "source_types": ["Not determined"],
                                "field_coverage": "Not determined"
                            }
                        },
                        "recommendations": {
                            "missing_citations": ["Not determined"],
                            "citation_improvements": ["Not determined"],
                            "key_papers_to_add": ["Not determined"]
                        }
                    }

        except Exception as e:
            print(f"OpenAI citation analysis error: {str(e)}")
            raise Exception(f"OpenAI citation analysis error: {str(e)}")

    async def analyze_research_gaps(self, text_content: str) -> Dict[str, Any]:
        """Identify research gaps and future opportunities"""
        try:
            completion = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": """Identify research gaps and opportunities.
                    Provide a JSON response with:
                    {
                        "research_gaps": {
                            "identified_gaps": ["list of gaps"],
                            "priority_levels": {
                                "high_priority": ["urgent gaps to address"],
                                "medium_priority": ["important but less urgent gaps"],
                                "low_priority": ["gaps that could be addressed"]
                            },
                            "gap_categories": {
                                "methodological": ["gaps in methods"],
                                "theoretical": ["gaps in theory"],
                                "empirical": ["gaps in data/evidence"]
                            }
                        },
                        "future_directions": {
                            "short_term": ["immediate research opportunities"],
                            "long_term": ["future research directions"],
                            "interdisciplinary": ["cross-field opportunities"]
                        },
                        "implementation": {
                            "required_resources": ["needed resources"],
                            "potential_challenges": ["anticipated challenges"],
                            "suggested_approaches": ["recommended methods"],
                            "collaboration_needs": ["required expertise"]
                        }
                    }"""},
                    {"role": "user", "content": f"Identify research gaps in this paper:\n\n{text_content}"}
                ]
            )
            
            content = completion.choices[0].message.content
            print(f"Gap analysis raw response: {content}")
            
            # Try to parse the response as JSON
            import json
            try:
                # Check if the response is already JSON
                return json.loads(content)
            except json.JSONDecodeError:
                # If not, try to extract JSON from markdown or text
                if "```json" in content:
                    # Extract JSON from markdown code block
                    json_str = content.split("```json")[1].split("```")[0].strip()
                    return json.loads(json_str)
                else:
                    # Create a fallback structure
                    print("Could not parse JSON from gap analysis response")
                    return {
                        "research_gaps": {
                            "identified_gaps": ["Not extracted"],
                            "priority_levels": {
                                "high_priority": ["Not determined"],
                                "medium_priority": ["Not determined"],
                                "low_priority": ["Not determined"]
                            },
                            "gap_categories": {
                                "methodological": ["Not determined"],
                                "theoretical": ["Not determined"],
                                "empirical": ["Not determined"]
                            }
                        },
                        "future_directions": {
                            "short_term": ["Not determined"],
                            "long_term": ["Not determined"],
                            "interdisciplinary": ["Not determined"]
                        },
                        "implementation": {
                            "required_resources": ["Not determined"],
                            "potential_challenges": ["Not determined"],
                            "suggested_approaches": ["Not determined"],
                            "collaboration_needs": ["Not determined"]
                        }
                    }

        except Exception as e:
            print(f"OpenAI research gap analysis error: {str(e)}")
            raise Exception(f"OpenAI research gap analysis error: {str(e)}")

    async def extract_text(self, image_path: str) -> str:
        """Extract text from image using OpenAI's vision capabilities"""
        try:
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
                
            completion = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Extract and transcribe all text from the provided image accurately."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64.b64encode(image_data).decode('utf-8')}"
                                }
                            },
                            {
                                "type": "text",
                                "text": "Please extract all text from this image, maintaining the original formatting."
                            }
                        ]
                    }
                ],
                temperature=0.1
            )

            return completion.choices[0].message.content

        except Exception as e:
            raise Exception(f"OpenAI OCR error: {str(e)}") 