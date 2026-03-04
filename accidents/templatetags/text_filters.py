# accidents/templatetags/text_filters.py
import re
from django import template
from django.template.defaultfilters import stringfilter
from django.utils import timezone

register = template.Library()

@register.filter
@stringfilter
def enhance_narrative(text):
    """
    Enhance narrative text by fixing common grammar and formatting issues
    """
    if not text:
        return text
    
    # Make a copy to work with
    enhanced = text.strip()
    
    # Fix time formatting (ensure colons in times)
    enhanced = re.sub(r'(\d{1,2})[\.\s](\d{2})', r'\1:\2', enhanced)  # 10.30 -> 10:30
    enhanced = re.sub(r'(\d{1,2})[\.\s](\d{2})\s*[ap]m', lambda m: f"{m.group(1)}:{m.group(2)}{m.group(0)[-2:]}", enhanced, flags=re.IGNORECASE)
    
    # Fix common abbreviations
    enhanced = re.sub(r'\b(\w+)\.(\w+)\.', r'\1.\2.', enhanced)  # Ensure proper dots in abbreviations
    
    # Ensure sentences start with capital letters
    sentences = re.split(r'([.!?]+\s+)', enhanced)
    enhanced = ''
    for i, sentence in enumerate(sentences):
        if i % 2 == 0:  # This is a sentence content
            if sentence.strip():
                # Capitalize first letter of sentence
                sentence = sentence[0].upper() + sentence[1:] if sentence else sentence
        enhanced += sentence
    
    # Fix spacing around punctuation
    enhanced = re.sub(r'\s+([.,!?;:])', r'\1', enhanced)  # Remove space before punctuation
    enhanced = re.sub(r'([.,!?;:])(\w)', r'\1 \2', enhanced)  # Add space after punctuation
    
    # Fix multiple spaces
    enhanced = re.sub(r'\s+', ' ', enhanced)
    
    return enhanced

@register.filter
@stringfilter
def format_time_display(time_str):
    """
    Format time for better display
    """
    if not time_str:
        return "Not recorded"
    
    # If it's already a time object passed as string
    if ':' in str(time_str):
        return str(time_str)
    
    # Fix common time formats
    time_str = str(time_str).strip()
    
    # Handle various time formats
    time_str = re.sub(r'(\d{1,2})[\.\s](\d{2})', r'\1:\2', time_str)
    time_str = re.sub(r'^(\d{1,2})$', r'\1:00', time_str)  # Single hour -> hour:00
    time_str = re.sub(r'^(\d{1,2})(\d{2})$', r'\1:\2', time_str)  # 1030 -> 10:30
    
    return time_str


@register.filter
def accident_age_badge(created_at):
    """
    Return badge type based on accident age:
    - 'new' if < 24 hours
    - '1 day ago', '2 days ago', etc. if < 7 days
    - '1 week ago' if 7-13 days
    - '2 weeks ago' if 14-29 days
    - '' (empty) if >= 30 days
    """
    if not created_at:
        return ''

    now = timezone.now()
    diff = now - created_at
    days = diff.days
    hours = diff.total_seconds() / 3600

    if hours < 24:
        return 'new'
    elif days < 7:
        return f'{days} day{"s" if days != 1 else ""} ago'
    elif days < 14:
        return '1 week ago'
    elif days < 30:
        return '2 weeks ago'
    return ''