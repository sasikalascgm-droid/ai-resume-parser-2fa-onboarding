from typing import List, Optional
from pydantic import BaseModel, Field


class ExtractedResumeData(BaseModel):
    full_name: Optional[str] = Field(default=None, description="Candidate full name")
    email: Optional[str] = Field(default=None, description="Candidate email address")
    phone: Optional[str] = Field(default=None, description="Candidate phone number")
    skills: List[str] = Field(default_factory=list, description="Extracted skills list")
    experience: Optional[str] = Field(default=None, description="Work experience summary")
    qualification: Optional[str] = Field(default=None, description="Highest qualification")


class ResumeParseResponse(BaseModel):
    success: bool = True
    resume_id: str
    original_filename: str
    extracted_data: ExtractedResumeData
    warnings: List[str] = Field(default_factory=list)
