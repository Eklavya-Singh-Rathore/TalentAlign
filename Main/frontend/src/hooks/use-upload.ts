import { useState } from "react";
import { useAnalysis } from "./use-analysis";
import { validateResumeFile, validateJobDescription } from "../lib/validators";

export function useUpload() {
  const { runAnalysis, setResumeFile, setJdText } = useAnalysis();
  const [file, setLocalFile] = useState<File | null>(null);
  const [jd, setLocalJd] = useState<string>("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      const check = validateResumeFile(droppedFile);
      if (check.isValid) {
        setLocalFile(droppedFile);
        setResumeFile(droppedFile);
        setValidationError(null);
      } else {
        setValidationError(check.error || "Invalid file");
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFile = e.target.files[0];
      const check = validateResumeFile(selectedFile);
      if (check.isValid) {
        setLocalFile(selectedFile);
        setResumeFile(selectedFile);
        setValidationError(null);
      } else {
        setValidationError(check.error || "Invalid file");
      }
    }
  };

  const handleJdChange = (text: string) => {
    setLocalJd(text);
    setJdText(text);
    if (validationError && text.trim().length >= 50) {
      setValidationError(null);
    }
  };

  const triggerAnalysis = async () => {
    if (!file) {
      setValidationError("Please select or drop a resume file first.");
      return;
    }
    
    const jdCheck = validateJobDescription(jd);
    if (!jdCheck.isValid) {
      setValidationError(jdCheck.error || "Invalid job description");
      return;
    }

    setValidationError(null);
    await runAnalysis(file, jd);
  };

  const clearSelection = () => {
    setLocalFile(null);
    setResumeFile(null);
    setLocalJd("");
    setJdText("");
    setValidationError(null);
  };

  return {
    file,
    jd,
    validationError,
    isDragging,
    handleDragOver,
    handleDragLeave,
    handleDrop,
    handleFileChange,
    handleJdChange,
    triggerAnalysis,
    clearSelection,
  };
}
