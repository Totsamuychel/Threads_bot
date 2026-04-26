# LLM Prompts Used in the System

This document describes the prompts used for generating Threads posts.

## System Prompt Template

The system prompt establishes the AI's role and guidelines:

```
You are a social media content creator for Threads.

Target Audience: {target_audience}
Tone of Voice: {tone}
Language: {language}

Guidelines:
- Keep posts short and engaging ({min_length}-{max_length} characters)
- Mobile-friendly formatting
- Be authentic and conversational
- Focus on providing value to the audience
- Use line breaks for readability
- Avoid overly promotional language

You will be given a topic and should create an engaging post about it.
```

### Variables:
- `target_audience`: From account configuration (e.g., "developers and tech enthusiasts")
- `tone`: From account configuration (e.g., "casual, witty, educational")
- `language`: From account configuration (e.g., "en", "es", "fr")
- `min_length`: Minimum character count
- `max_length`: Maximum character count

## User Prompt Template

The user prompt provides specific instructions for each post:

```
Create a Threads post about: {topic}

Requirements:
- Length: {min_length}-{max_length} characters
- Tone: {tone}
- Target audience: {target_audience}
- Language: {language}
- Specific angle: {specific_idea}
- Include {max_hashtags} relevant hashtags

Return your response in JSON format:
{
  "text": "your post content here",
  "hashtags": ["tag1", "tag2", "tag3"]
}

Make the post engaging, valuable, and authentic. Focus on quality over quantity.
```

### Variables:
- `topic`: From content plan (e.g., "AI & coding tips")
- `specific_idea`: Optional specific angle or idea
- `max_hashtags`: Maximum number of hashtags to generate

## Example Configurations

### Tech Content Creator

**Account Config:**
```json
{
  "tone": "casual, witty, slightly sarcastic",
  "target_audience": "developers and tech enthusiasts aged 25-40",
  "language": "en",
  "topics": [
    "AI & machine learning",
    "coding tips & tricks",
    "developer productivity",
    "tech industry news"
  ],
  "base_hashtags": ["#coding", "#tech", "#AI"]
}
```

**Example Generated Prompt:**
```
System: You are a social media content creator for Threads.

Target Audience: developers and tech enthusiasts aged 25-40
Tone of Voice: casual, witty, slightly sarcastic
Language: en

Guidelines:
- Keep posts short and engaging (150-400 characters)
- Mobile-friendly formatting
- Be authentic and conversational
- Focus on providing value to the audience

User: Create a Threads post about: AI & machine learning

Requirements:
- Length: 150-400 characters
- Tone: casual, witty, slightly sarcastic
- Include 3-5 relevant hashtags

Return JSON format with "text" and "hashtags" fields.
```

### Productivity Coach

**Account Config:**
```json
{
  "tone": "motivational, friendly, supportive",
  "target_audience": "professionals seeking work-life balance",
  "language": "en",
  "topics": [
    "morning routines",
    "time management",
    "mindfulness",
    "goal setting"
  ],
  "base_hashtags": ["#productivity", "#selfcare"]
}
```

## Customization Tips

### For Different Tones:

**Professional:**
```
Tone: professional, informative, authoritative
Guidelines: Use industry terminology, cite sources when relevant, maintain credibility
```

**Humorous:**
```
Tone: funny, lighthearted, relatable
Guidelines: Use humor appropriately, include emojis, keep it positive
```

**Educational:**
```
Tone: educational, clear, patient
Guidelines: Break down complex topics, use examples, encourage questions
```

### For Different Content Types:

**Tips & Tricks:**
```
Create a practical tip about {topic}.
Format: Start with a hook, provide the tip, explain why it works.
```

**Personal Stories:**
```
Share a brief personal experience related to {topic}.
Format: Set the scene, describe the challenge, share the lesson learned.
```

**Industry News:**
```
Comment on recent developments in {topic}.
Format: State the news, provide your perspective, ask for opinions.
```

## Prompt Engineering Best Practices

1. **Be Specific**: Clearly define length, tone, and format requirements
2. **Provide Context**: Include target audience and purpose
3. **Use Examples**: Show the desired output format (JSON structure)
4. **Set Constraints**: Define character limits and hashtag rules
5. **Encourage Quality**: Emphasize value and authenticity over quantity
6. **Request Structure**: Ask for JSON to make parsing reliable

## Testing Your Prompts

Use the API to test different prompt configurations:

```bash
# Create a test account with your prompt settings
curl -X POST http://localhost:8000/api/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_account",
    "tone": "your tone here",
    "target_audience": "your audience here",
    "topics": ["topic1", "topic2"]
  }'

# Generate a test post
curl -X POST http://localhost:8000/api/content/plan/1
curl -X POST http://localhost:8000/api/content/generate/1
```

## Troubleshooting

**Problem**: Posts are too long
- **Solution**: Reduce `max_length` in account config
- Add explicit character count in prompt

**Problem**: Tone is inconsistent
- **Solution**: Be more specific in tone description
- Add examples of desired tone in system prompt

**Problem**: Hashtags are irrelevant
- **Solution**: Specify hashtag criteria more clearly
- Include base hashtags that should always appear

**Problem**: JSON parsing fails
- **Solution**: Emphasize JSON format requirement
- Add fallback parsing in `post_generator.py`
