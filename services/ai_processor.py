import openai
import json
import re
from datetime import datetime, timedelta
from django.conf import settings
from main_app.models import (
    JobCard, JobCardAction, Customer, Order, OrderItem, 
    Payment, Item, AIProcessingLog
)


class AITextProcessor:
    """
    AI-powered text processing service for field reports
    Extracts structured data from natural language field reports
    """
    
    def __init__(self):
        openai.api_key = getattr(settings, 'OPENAI_API_KEY', '')
    
    def process_field_report(self, jobcard_action_id):
        """
        Process field report text and extract structured data
        """
        try:
            action = JobCardAction.objects.get(id=jobcard_action_id)
            
            # Create processing log
            log = AIProcessingLog.objects.create(
                jobcard_action=action,
                input_text=action.note_text,
                status='PROCESSING'
            )
            
            # Process with OpenAI
            processed_data = self._extract_entities(action.note_text)
            
            # Update log with results
            log.processed_data = processed_data
            log.confidence_score = processed_data.get('confidence', 0.0)
            log.status = 'COMPLETED'
            log.processed_at = datetime.now()
            log.save()
            
            # Create follow-up tasks if needed
            self._create_followup_tasks(action, processed_data)
            
            # Update job card with extracted data
            self._update_jobcard_data(action, processed_data)
            
            return processed_data
            
        except Exception as e:
            log.status = 'FAILED'
            log.error_message = str(e)
            log.save()
            raise e
    
    def _extract_entities(self, text):
        """
        Use OpenAI to extract entities from field report text
        """
        prompt = f"""
        Extract structured information from this field visit report:
        "{text}"
        
        Please extract and return a JSON object with the following fields:
        - customer_name: Name of the customer/company visited
        - contact_person: Name of the person met
        - visit_outcome: Summary of what happened (order, payment, complaint, etc.)
        - order_details: If order was taken (item, quantity, rate, amount)
        - payment_details: If payment was collected (method, amount, cheque numbers)
        - follow_up_required: If follow-up is needed (yes/no)
        - follow_up_date: When to follow up (if mentioned)
        - follow_up_reason: Why follow-up is needed
        - confidence: Confidence score (0-1) for the extraction
        
        Return only valid JSON format.
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an AI assistant that extracts structured data from sales field reports. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            result = response.choices[0].message.content.strip()
            
            # Try to parse JSON
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                # Fallback to regex extraction
                return self._fallback_extraction(text)
                
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return self._fallback_extraction(text)
    
    def _fallback_extraction(self, text):
        """
        Fallback extraction using regex patterns
        """
        extracted = {
            'customer_name': '',
            'contact_person': '',
            'visit_outcome': 'visit_completed',
            'order_details': {},
            'payment_details': {},
            'follow_up_required': 'no',
            'follow_up_date': '',
            'follow_up_reason': '',
            'confidence': 0.6
        }
        
        # Extract customer names (common patterns)
        customer_patterns = [
            r'(?:met|visited|at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:company|ltd|pvt)',
        ]
        
        for pattern in customer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted['customer_name'] = match.group(1)
                break
        
        # Extract order quantities
        qty_pattern = r'(\d+)\s*(?:bales?|kg|tons?)'
        qty_match = re.search(qty_pattern, text, re.IGNORECASE)
        if qty_match:
            extracted['order_details']['quantity'] = int(qty_match.group(1))
        
        # Extract rates/prices
        rate_pattern = r'(?:rate|price|₹)\s*(\d+(?:,\d+)*)'
        rate_match = re.search(rate_pattern, text, re.IGNORECASE)
        if rate_match:
            extracted['order_details']['rate'] = float(rate_match.group(1).replace(',', ''))
        
        # Extract payment amounts
        payment_pattern = r'(?:collected|received|paid)\s*₹?\s*(\d+(?:,\d+)*)'
        payment_match = re.search(payment_pattern, text, re.IGNORECASE)
        if payment_match:
            extracted['payment_details']['amount'] = float(payment_match.group(1).replace(',', ''))
        
        # Check for follow-up indicators
        followup_keywords = ['follow', 'call back', 'visit again', 'after', 'next week', 'tomorrow']
        if any(keyword in text.lower() for keyword in followup_keywords):
            extracted['follow_up_required'] = 'yes'
            extracted['follow_up_reason'] = 'mentioned in report'
        
        return extracted
    
    def _create_followup_tasks(self, action, processed_data):
        """
        Create follow-up job cards based on extracted data
        """
        if processed_data.get('follow_up_required') == 'yes':
            # Calculate follow-up date
            follow_up_date = None
            if processed_data.get('follow_up_date'):
                try:
                    # Try to parse date from text
                    follow_up_date = self._parse_date(processed_data['follow_up_date'])
                except:
                    # Default to 3 days from now
                    follow_up_date = datetime.now() + timedelta(days=3)
            else:
                follow_up_date = datetime.now() + timedelta(days=3)
            
            # Create follow-up job card
            JobCard.objects.create(
                type='FOLLOWUP',
                priority='MEDIUM',
                status='PENDING',
                assigned_to=action.jobcard.assigned_to,
                customer=action.jobcard.customer,
                city=action.jobcard.city,
                due_at=follow_up_date,
                created_by=action.actor,
                created_reason=f"Auto-generated from field report: {processed_data.get('follow_up_reason', 'Follow-up required')}",
                related_item=action.jobcard.related_item
            )
    
    def _update_jobcard_data(self, action, processed_data):
        """
        Update job card with extracted structured data
        """
        # Update the action's structured_json field
        action.structured_json = processed_data
        action.save()
        
        # Mark original job card as completed if visit was successful
        if processed_data.get('visit_outcome') in ['order_taken', 'payment_collected', 'visit_completed']:
            action.jobcard.status = 'COMPLETED'
            action.jobcard.save()
    
    def _parse_date(self, date_text):
        """
        Parse date from natural language text
        """
        # Simple date parsing - can be enhanced
        today = datetime.now()
        
        if 'tomorrow' in date_text.lower():
            return today + timedelta(days=1)
        elif 'next week' in date_text.lower():
            return today + timedelta(days=7)
        elif 'after' in date_text.lower():
            # Extract number of days
            match = re.search(r'after\s+(\d+)\s+days?', date_text.lower())
            if match:
                days = int(match.group(1))
                return today + timedelta(days=days)
        
        # Default to 3 days
        return today + timedelta(days=3)


# Example usage and test function
def test_ai_processor():
    """
    Test function for AI processor
    """
    processor = AITextProcessor()
    
    test_text = """
    Met Sahil at Tallam Brothers, collected order for 5 bales of 40s cut, 
    rate ₹215, took 2 cheques, he will transfer funds online after 3 days 
    for XYZ company
    """
    
    result = processor._extract_entities(test_text)
    print("Extracted data:", json.dumps(result, indent=2))
    
    return result
