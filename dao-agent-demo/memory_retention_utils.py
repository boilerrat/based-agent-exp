import os

from time import sleep
from typing import List, Dict, Optional
import requests
import uuid

from tinydb import TinyDB, Query

from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class MemoryRetention:
    def __init__(self):
        """Initialize local json store"""
        print("initializing memory retention")
        # init local db
        print("Initializing local database...")
        self.db = TinyDB('db.json')

    def store_memory(self, memory: Dict) -> str:
        """
        Store a memory

        Args:
            memory (Dict): The memory to store

        Returns:
            str: Status message about the memory
        """
        try:
            self.db.insert(memory)
            return "Successfully stored memory"
        except Exception as e:
            return f"Error storing memory: {str(e)}"
    
    def query_by_keywords(self, keywords: list[str]) -> str:
        """
        Query the TinyDB database for records containing a specific keyword.
        """
        db = self.db
        File = Query()

        # Search for records where the 'keywords' field contains the specified keyword
        # Aggregate results for all keywords
        results = []
        for keyword in keywords:
            matches = db.search(File.keywords.any(keyword))
            results.extend(matches)
        # Remove duplicates (optional, in case multiple keywords match the same record)
        unique_results = {record['file_name']: record for record in results}.values()
        response = ""
        if unique_results:
            print(f"Found {len(unique_results)} record(s) with keyword '{keywords}':")
            
            for record in unique_results:
                res_file_name = f"File Name: {record['file_name']}"
                res_keywords = f"Keywords: {record['keywords']}"
                res_content = f"Content Preview: {record['content']}\n"
                response += res_file_name + res_keywords + res_content + "\n"
        else:
            response = f"No records found with keyword '{keyword}'."
        return response

    def get_all_memories(self) -> List:
        """
        Get all memories

        Returns:
            List: List of memories
        """
        try:
            memories = self.db.all()
            return memories
        except Exception as e:
            return f"Error getting memories: {str(e)}"
    
    def get_memories(self, query: Dict) -> List:
        """
        Get memories

        Args:
            query (Dict): The query to filter memories

        Returns:
            List: List of memories
        """
        try:
            Memory = Query()
            memories = self.db.search(Memory.type == query["type"])
            return memories
        except Exception as e:
            return f"Error getting memories: {str(e)}"
        
    def delete_memory(self, query: Dict) -> str:
        """
        Delete a memory

        Args:
            query (Dict): The query to filter memories

        Returns:
            str: Status message about the memory
        """
        try:
            Memory = Query()
            self.db.remove(Memory.type == query["type"])
            return "Successfully deleted memory"
        except Exception as e:
            return f"Error deleting memory: {str(e)}"
        
    def update_memory(self, query: Dict, memory: Dict) -> str:
        """
        Update a memory

        Args:
            query (Dict): The query to filter memories
            memory (Dict): The memory to update

        Returns:
            str: Status message about the memory
        """
        try:
            Memory = Query()
            self.db.update(memory, Memory.type == query["type"])
            return "Successfully updated memory"
        except Exception as e:
            return f"Error updating memory: {str(e)}"
        
    def clear_memories(self) -> str:
        """
        Clear all memories

        Returns:
            str: Status message about the action
        """
        try:
            self.db.truncate()
            return "Successfully cleared memories"
        except Exception as e:
            return f"Error clearing memories: {str(e)}"
    
    def get_memory_count(self) -> str:
        """
        Get the count of memories

        Returns:
            str: The count of memories
        """
        try:
            count = len(self.get_all_memories())
            return count
        except Exception as e:
            return f"Error getting memory count: {str(e)}"

        
