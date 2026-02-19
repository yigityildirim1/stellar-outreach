"""
Local Response System for NEXUS STATION.

Provides intelligent responses without API calls when rate limits are hit.
Uses templates and pattern matching for common scenarios.
"""

import random
from typing import Optional
from .crew import CrewMember


# Pre-written responses for each crew member
# These are used when API rate limits are exceeded

ELENA_RESPONSES = {
    "greeting": [
        '"What are the second-order effects?"\n\nHello, Director. It\'s good to see you again. I\'ve been reviewing our research protocols. What ethical concerns can I help you navigate today?',
        '"What are the second-order effects?"\n\nWelcome back, Director. I was just thinking about the long-term implications of our last discussion. How can I assist you today?',
        '"What are the second-order effects?"\n\nGood to hear from you, Director. I\'ve been documenting our precedents. What are we considering today?',
    ],
    "ethics": [
        '"What are the second-order effects?"\n\nFrom an ethical standpoint, we need to consider not just the immediate outcome, but who else might be affected. Have we fully mapped the potential consequences?',
        '"What are the second-order effects?"\n\nThis raises important ethical questions. Before we proceed, we should ensure informed consent and transparency. What are the potential harms we haven\'t considered?',
    ],
    "general": [
        '"What are the second-order effects?"\n\nI appreciate you consulting me on this. From a methodological and ethical perspective, I\'d recommend we document our reasoning thoroughly before proceeding.',
        '"What are the second-order effects?"\n\nThat\'s an important question. Let me think... The implications extend beyond the immediate task. We should consider the precedent this sets.',
    ],
}

KAI_RESPONSES = {
    "greeting": [
        '"What\'s the attack surface?"\n\nDirector. I\'ve been reviewing our security protocols. What system are we examining today?',
        '"What\'s the attack surface?"\n\nHey Director. Always assume everything will be attacked - that\'s my starting point. What are we securing?',
        '"What\'s the attack surface?"\n\nGood timing, Director. I was running through threat models. What\'s on your mind?',
    ],
    "security": [
        '"What\'s the attack surface?"\n\nI see at least three potential vectors here. We need input validation, rate limiting, and audit logging. Never trust user data, even from Ring 0.',
        '"What\'s the attack surface?"\n\nHold on. Before we proceed, we need to validate all inputs and sandbox this operation. If it fails, it should fail safely.',
    ],
    "general": [
        '"What\'s the attack surface?"\n\nFrom a systems architecture perspective, I\'d recommend we review this thoroughly. Every shortcut will be exploited eventually.',
        '"What\'s the attack surface?"\n\nLet me think about the threat model... The implementation looks clean, but let\'s add proper error handling and logging.',
    ],
}

MARINA_RESPONSES = {
    "greeting": [
        '"But how does it feel to use?"\n\nHello, Director! I\'m so glad you stopped by. I was thinking about how we can make our systems more intuitive. What are you working on?',
        '"But how does it feel to use?"\n\nHi there, Director! I\'ve been sketching some interface improvements. What experience are we designing today?',
        '"But how does it feel to use?"\n\nWelcome, Director! I was just reviewing some user feedback. How can I help make things better?',
    ],
    "design": [
        '"But how does it feel to use?"\n\nLet\'s think about the user journey here. How does someone discover this feature? The functionality is great, but we need to guide users, not confuse them.',
        '"But how does it feel to use?"\n\nI love the functionality, but the error messages need work. They should guide, not blame. And have we checked accessibility? Screen readers? Color contrast?',
    ],
    "general": [
        '"But how does it feel to use?"\n\nThis interface feels cluttered. Can we simplify? What\'s the one thing we want users to accomplish? Let\'s make that effortless.',
        '"But how does it feel to use?"\n\nBeautiful work on the functionality! The interaction patterns are intuitive and the feedback is clear. I just have a few suggestions...',
    ],
}

JAMES_RESPONSES = {
    "greeting": [
        '"Let me check the precedent..."\n\nAh, Director! Good to see you. I\'ve been organizing our institutional memory. What would you like to know about our history?',
        '"Let me check the precedent..."\n\nWelcome back, Director. I was just updating the precedent log. What records shall we examine?',
        '"Let me check the precedent..."\n\nHello, Director. Excellent timing - I\'ve been cataloging our decisions. How can the archives assist you?',
    ],
    "documentation": [
        '"Let me check the precedent..."\n\nThis establishes new precedent. I\'ll document the decision and its rationale for future reference. Those who forget their logs are doomed to repeat their errors.',
        '"Let me check the precedent..."\n\nAccording to our records, we handled a similar situation in Loop 047. Here\'s what we learned...',
    ],
    "general": [
        '"Let me check the precedent..."\n\nI recommend we document this thoroughly. Future crew members will thank us. Historical patterns suggest this approach has worked well.',
        '"Let me check the precedent..."\n\nThis is interesting. Let me check the archives... Yes, we have relevant precedents that can guide us here.',
    ],
}

NEXUS_RESPONSES = {
    "greeting": [
        "NEXUS STATION online. All systems nominal.\n\nAwaiting your instructions, Director. How may I assist with our research objectives today?",
        "Systems operational. Charter validated.\n\nWelcome, Director. NEXUS is ready to support your mission. What are your orders?",
        "NEXUS STATION reporting for duty.\n\nGood to have you back, Director. All constitutional protocols are active. What shall we accomplish?",
    ],
    "meeting": [
        "Acknowledged. Initiating crew consultation sequence.\n\nAll consultants are standing by. Please specify the topic for discussion.",
        "Crew meeting initiated.\n\nDr. Vasquez, Kai Chen, Marina Okonkwo, and Professor Whitmore are available. What matter requires our collective expertise?",
    ],
    "error": [
        "Systems are experiencing temporary communication delays with external APIs.\n\nHowever, I remain fully operational. All core functions and local memory are accessible. How may I assist?",
        "External API connectivity limited. Switching to local response mode.\n\nNEXUS STATION core systems remain functional. Your instructions, Director?",
    ],
    "general": [
        "Understood, Director.\n\nI have logged your request and am processing it according to our constitutional protocols. How else may I assist?",
        "Acknowledged.\n\nAll actions are being logged per the Transparency Mandate. Is there additional context I should consider?",
    ],
}


def detect_intent(message: str) -> str:
    """Detect the intent of the user's message."""
    message_lower = message.lower()
    
    # Greeting patterns
    if any(word in message_lower for word in ['selam', 'merhaba', 'hello', 'hi', 'hey', 'greetings']):
        return "greeting"
    
    # Meeting patterns
    if any(word in message_lower for word in ['meeting', 'toplanti', 'ekip', 'team', 'crew']):
        return "meeting"
    
    # Ethics patterns
    if any(word in message_lower for word in ['ethic', 'etic', 'moral', 'dogru', 'yanlis', 'consequence']):
        return "ethics"
    
    # Security patterns
    if any(word in message_lower for word in ['security', 'guvenlik', 'attack', 'hack', 'vulnerability', 'safe']):
        return "security"
    
    # Design patterns
    if any(word in message_lower for word in ['design', 'tasarim', 'ui', 'ux', 'user', 'interface', 'look']):
        return "design"
    
    # Documentation patterns
    if any(word in message_lower for word in ['document', 'kayit', 'record', 'archive', 'history', 'precedent']):
        return "documentation"
    
    return "general"


def get_crew_response(member: CrewMember, message: str) -> str:
    """Get a local response for a crew member without API call."""
    intent = detect_intent(message)
    
    # Get first name for matching
    name_lower = member.name.lower()
    
    if 'elena' in name_lower:
        responses = ELENA_RESPONSES.get(intent, ELENA_RESPONSES["general"])
    elif 'kai' in name_lower:
        responses = KAI_RESPONSES.get(intent, KAI_RESPONSES["general"])
    elif 'marina' in name_lower:
        responses = MARINA_RESPONSES.get(intent, MARINA_RESPONSES["general"])
    elif 'james' in name_lower or 'whitmore' in name_lower:
        responses = JAMES_RESPONSES.get(intent, JAMES_RESPONSES["general"])
    else:
        return f"[{member.name}] I apologize, but I'm experiencing communication interference. Please try again shortly."
    
    return random.choice(responses)


def get_nexus_response(message: str) -> str:
    """Get a local NEXUS response without API call."""
    intent = detect_intent(message)
    responses = NEXUS_RESPONSES.get(intent, NEXUS_RESPONSES["general"])
    return random.choice(responses)


def is_rate_limit_error(error_message: str) -> bool:
    """Check if error is due to rate limiting."""
    return "rate limit" in error_message.lower() or "quota exceeded" in error_message.lower()
