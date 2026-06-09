export function validateResumeFile(file: File): { isValid: boolean; error?: string } {
  const allowedExtensions = [".pdf", ".docx"];
  const maxBytes = 10 * 1024 * 1024; // 10 MB
  
  const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
  
  if (!allowedExtensions.includes(ext)) {
    return {
      isValid: false,
      error: `Unsupported file type '${ext}'. Please upload a .pdf or .docx resume.`,
    };
  }
  
  if (file.size > maxBytes) {
    return {
      isValid: false,
      error: "File is too large (maximum limit is 10 MB).",
    };
  }
  
  if (file.size === 0) {
    return {
      isValid: false,
      error: "Uploaded file is empty.",
    };
  }
  
  return { isValid: true };
}

export function validateJobDescription(text: string): { isValid: boolean; error?: string } {
  if (!text || !text.trim()) {
    return {
      isValid: false,
      error: "Job description text must be a non-empty string.",
    };
  }
  
  if (text.trim().length < 50) {
    return {
      isValid: false,
      error: "Job description seems too short. Please paste a more detailed description.",
    };
  }
  
  return { isValid: true };
}
