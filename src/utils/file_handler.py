"""
File handling utilities for Clippy
"""

import os
import shutil
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import json
import pickle
from datetime import datetime

from loguru import logger


class FileHandler:
    """Utilities for file operations and management"""
    
    def __init__(self, base_path: str = "."):
        """Initialize file handler with base path"""
        self.base_path = Path(base_path)
        self.ensure_base_directories()
    
    def ensure_base_directories(self):
        """Ensure base directories exist"""
        directories = [
            "downloads",
            "output", 
            "temp",
            "logs",
            "models",
            "cache"
        ]
        
        for directory in directories:
            dir_path = self.base_path / directory
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def get_file_hash(self, file_path: Union[str, Path]) -> str:
        """Generate MD5 hash of file content"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
            
        except Exception as e:
            logger.error(f"❌ Error generating file hash: {e}")
            return ""
    
    def get_file_info(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Get comprehensive file information"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return {"error": "File not found"}
            
            stat = file_path.stat()
            
            return {
                "name": file_path.name,
                "path": str(file_path.absolute()),
                "size": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": file_path.suffix.lower(),
                "is_file": file_path.is_file(),
                "is_directory": file_path.is_dir(),
                "hash": self.get_file_hash(file_path) if file_path.is_file() else None
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting file info: {e}")
            return {"error": str(e)}
    
    def safe_filename(self, filename: str, max_length: int = 255) -> str:
        """Create safe filename by removing invalid characters"""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        safe_name = filename
        
        for char in invalid_chars:
            safe_name = safe_name.replace(char, '_')
        
        # Remove leading/trailing spaces and dots
        safe_name = safe_name.strip(' .')
        
        # Truncate if too long
        if len(safe_name) > max_length:
            name_part = safe_name[:max_length-10]
            ext_part = Path(filename).suffix
            safe_name = name_part + ext_part
        
        return safe_name
    
    def copy_file(self, source: Union[str, Path], destination: Union[str, Path], 
                  overwrite: bool = False) -> bool:
        """Copy file with error handling"""
        try:
            source = Path(source)
            destination = Path(destination)
            
            if not source.exists():
                logger.error(f"❌ Source file not found: {source}")
                return False
            
            if destination.exists() and not overwrite:
                logger.warning(f"⚠️ Destination exists and overwrite=False: {destination}")
                return False
            
            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(source, destination)
            logger.info(f"📁 Copied file: {source} → {destination}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error copying file: {e}")
            return False
    
    def move_file(self, source: Union[str, Path], destination: Union[str, Path], 
                  overwrite: bool = False) -> bool:
        """Move file with error handling"""
        try:
            source = Path(source)
            destination = Path(destination)
            
            if not source.exists():
                logger.error(f"❌ Source file not found: {source}")
                return False
            
            if destination.exists() and not overwrite:
                logger.warning(f"⚠️ Destination exists and overwrite=False: {destination}")
                return False
            
            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(source), str(destination))
            logger.info(f"📁 Moved file: {source} → {destination}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error moving file: {e}")
            return False
    
    def delete_file(self, file_path: Union[str, Path], force: bool = False) -> bool:
        """Delete file with confirmation"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                logger.warning(f"⚠️ File not found: {file_path}")
                return True  # Consider it successful if already gone
            
            if file_path.is_dir():
                if force:
                    shutil.rmtree(file_path)
                    logger.info(f"🗑️ Deleted directory: {file_path}")
                else:
                    logger.error(f"❌ Cannot delete directory without force=True: {file_path}")
                    return False
            else:
                file_path.unlink()
                logger.info(f"🗑️ Deleted file: {file_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting file: {e}")
            return False
    
    def cleanup_directory(self, directory: Union[str, Path], 
                         pattern: str = "*", older_than_days: int = None) -> int:
        """Clean up files in directory matching pattern"""
        try:
            directory = Path(directory)
            
            if not directory.exists():
                logger.warning(f"⚠️ Directory not found: {directory}")
                return 0
            
            deleted_count = 0
            cutoff_time = None
            
            if older_than_days:
                cutoff_time = datetime.now().timestamp() - (older_than_days * 24 * 3600)
            
            for file_path in directory.glob(pattern):
                if file_path.is_file():
                    delete_file = True
                    
                    if cutoff_time:
                        file_time = file_path.stat().st_mtime
                        delete_file = file_time < cutoff_time
                    
                    if delete_file:
                        if self.delete_file(file_path):
                            deleted_count += 1
            
            logger.info(f"🧹 Cleaned up {deleted_count} files from {directory}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up directory: {e}")
            return 0
    
    def save_json(self, data: Any, file_path: Union[str, Path], 
                  indent: int = 2, ensure_ascii: bool = False) -> bool:
        """Save data to JSON file"""
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii, default=str)
            
            logger.debug(f"💾 Saved JSON: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving JSON: {e}")
            return False
    
    def load_json(self, file_path: Union[str, Path]) -> Optional[Any]:
        """Load data from JSON file"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                logger.warning(f"⚠️ JSON file not found: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.debug(f"📖 Loaded JSON: {file_path}")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error loading JSON: {e}")
            return None
    
    def save_pickle(self, data: Any, file_path: Union[str, Path]) -> bool:
        """Save data to pickle file"""
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'wb') as f:
                pickle.dump(data, f)
            
            logger.debug(f"💾 Saved pickle: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving pickle: {e}")
            return False
    
    def load_pickle(self, file_path: Union[str, Path]) -> Optional[Any]:
        """Load data from pickle file"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                logger.warning(f"⚠️ Pickle file not found: {file_path}")
                return None
            
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
            
            logger.debug(f"📖 Loaded pickle: {file_path}")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error loading pickle: {e}")
            return None
    
    def get_directory_size(self, directory: Union[str, Path]) -> Dict[str, Any]:
        """Get directory size information"""
        try:
            directory = Path(directory)
            
            if not directory.exists():
                return {"error": "Directory not found"}
            
            total_size = 0
            file_count = 0
            dir_count = 0
            
            for item in directory.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
                    file_count += 1
                elif item.is_dir():
                    dir_count += 1
            
            return {
                "path": str(directory.absolute()),
                "total_size": total_size,
                "size_mb": round(total_size / (1024 * 1024), 2),
                "size_gb": round(total_size / (1024 * 1024 * 1024), 2),
                "file_count": file_count,
                "directory_count": dir_count
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting directory size: {e}")
            return {"error": str(e)}
    
    def find_files(self, directory: Union[str, Path], pattern: str = "*", 
                   recursive: bool = True, max_results: int = None) -> List[Dict[str, Any]]:
        """Find files matching pattern"""
        try:
            directory = Path(directory)
            
            if not directory.exists():
                return []
            
            files = []
            search_method = directory.rglob if recursive else directory.glob
            
            for file_path in search_method(pattern):
                if file_path.is_file():
                    file_info = self.get_file_info(file_path)
                    files.append(file_info)
                    
                    if max_results and len(files) >= max_results:
                        break
            
            return files
            
        except Exception as e:
            logger.error(f"❌ Error finding files: {e}")
            return []
    
    def get_disk_usage(self, path: Union[str, Path] = ".") -> Dict[str, Any]:
        """Get disk usage information"""
        try:
            import shutil
            
            total, used, free = shutil.disk_usage(path)
            
            return {
                "path": str(Path(path).absolute()),
                "total": total,
                "used": used,
                "free": free,
                "total_gb": round(total / (1024 * 1024 * 1024), 2),
                "used_gb": round(used / (1024 * 1024 * 1024), 2),
                "free_gb": round(free / (1024 * 1024 * 1024), 2),
                "used_percent": round((used / total) * 100, 1)
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting disk usage: {e}")
            return {"error": str(e)}
    
    def backup_file(self, file_path: Union[str, Path], backup_dir: str = "backups") -> Optional[Path]:
        """Create backup of file with timestamp"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                logger.error(f"❌ File not found for backup: {file_path}")
                return None
            
            backup_directory = self.base_path / backup_dir
            backup_directory.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
            backup_path = backup_directory / backup_name
            
            if self.copy_file(file_path, backup_path):
                logger.info(f"💾 Created backup: {backup_path}")
                return backup_path
            else:
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating backup: {e}")
            return None
    
    def compress_directory(self, directory: Union[str, Path], 
                          output_path: Union[str, Path] = None) -> Optional[Path]:
        """Compress directory to ZIP file"""
        try:
            import zipfile
            
            directory = Path(directory)
            
            if not directory.exists():
                logger.error(f"❌ Directory not found: {directory}")
                return None
            
            if not output_path:
                output_path = directory.parent / f"{directory.name}.zip"
            else:
                output_path = Path(output_path)
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in directory.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(directory)
                        zipf.write(file_path, arcname)
            
            logger.info(f"📦 Compressed directory: {directory} → {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Error compressing directory: {e}")
            return None


# Global file handler instance
file_handler = FileHandler()
