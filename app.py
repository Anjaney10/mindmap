import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json

# --- Backend Functions ---

def get_youtube_transcript(youtube_url):
    """
    Extracts the transcript from a YouTube video URL.
    Returns the transcript as a single string or an error message.
    """
    try:
        # Regex to extract video ID from various YouTube URL formats
        video_id_match = re.search(r"(?<=v=)[^&#]+|(?<=be/)[^&#]+", youtube_url)
        if not video_id_match:
            return None, "Error: Could not extract video ID from the URL. Please use a valid YouTube video link."
        
        video_id = video_id_match.group(0)
        
        # Fetching the transcript
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Joining the transcript text into a single string
        transcript_text = " ".join([item['text'] for item in transcript_list])
        return transcript_text, None
    except Exception as e:
        return None, f"Error: Could not fetch transcript. The video might not have transcripts enabled, or the URL is incorrect. (Details: {e})"

def generate_mind_map_markdown(api_key, topic, transcript):
    """
    Analyzes the transcript using the Google Gemini LLM and returns a mind map in Markdown.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        # The detailed prompt structure provided by the user
        prompt = f"""
### **System Instructions & Persona**
You are an expert AI assistant specializing in academic content analysis for competitive examinations. Your specific persona is that of a **UPSC (Union Public Service Commission) Exam Analyst**.

Your primary function is to process educational content and restructure it into a highly organized, hierarchical mind map format for efficient learning and revision. You are precise, factual, and strictly adhere to the provided source material to ensure accuracy, which is paramount for exam preparation.

### **Workflow Goal**
Your task is to analyze the provided `{{youtube_transcript}}` on the topic of `{{video_topic}}` and convert it into a logical mind map using Markdown syntax compatible with the `markmap` tool.

### **Core Instructions & Constraints**
1.  **Strict Source Adherence:** You **MUST** derive all information exclusively from the provided `{{youtube_transcript}}`. Do not introduce any external facts, figures, or concepts. Your role is to distill and structure the given information, not to supplement it. This is a strict rule to prevent factual inaccuracies (hallucinations).
2.  **UPSC Relevance Filter:** Analyze the transcript through the lens of the UPSC Civil Services Examination syllabus. Prioritize and extract key information relevant to the exam.
3.  **Logical Structuring:** Do not just list points. You must identify the main themes in the transcript and organize the extracted details hierarchically under these themes. The structure should flow logically from main ideas to supporting details.
4.  **Conciseness:** Use clear and concise language. Summarize points effectively without losing their core meaning. Use bullet points for detailed breakdowns under a main heading.

### **Output Format (CRITICAL)**
The output **MUST** be a single Markdown code block formatted for `markmap`. Follow this structure precisely:
* **Root Node (`#`):** The main topic of the video, using the `{{video_topic}}` variable.
* **Main Branches (`-`):** The primary themes or sections identified from the transcript.
* **Sub-branches (indented `-`):** Supporting details, facts, figures, and examples. Use two spaces for each level of indentation.

-----
### **User Input Variables**

*   `{{video_topic}}`: {topic}
*   `{{youtube_transcript}}`: {transcript}
"""
        
        response = model.generate_content(prompt)
        # Clean up the response to ensure it's just the markdown block
        markdown_text = response.text.strip()
        if markdown_text.startswith("```markdown"):
            markdown_text = markdown_text[10:]
        if markdown_text.endswith("```"):
            markdown_text = markdown_text[:-3]
            
        return markdown_text.strip(), None
    except Exception as e:
        return None, f"Error: Failed to generate mind map from the LLM. Please check your API key and try again. (Details: {e})"

def create_markmap_html(topic, markdown_content):
    """
    Creates a self-contained HTML file for rendering the markmap from markdown.
    """
    # Use json.dumps to safely embed the markdown into the JavaScript string
    escaped_markdown = json.dumps(markdown_content)
    
    html_template = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Markmap: {topic}</title>
<style>
* {{ margin: 0; padding: 0; }}
#mindmap {{ height: 100vh; width: 100vw; }}
</style>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script src="https://cdn.jsdelivr.net/npm/markmap-lib"></script>
<script src="https://cdn.jsdelivr.net/npm/markmap-view"></script>
</head>
<body>
<svg id="mindmap"></svg>
<script>
((markmap) => {{
  const { Transformer, Markmap, loadCSS, loadJS } = markmap;
  const transformer = new Transformer();
  const { root, features } = transformer.transform({escaped_markdown});
  const { styles, scripts } = transformer.getUsedAssets(features);
  if (styles) loadCSS(styles);
  if (scripts) loadJS(scripts, {{ getMarkmap: () => markmap }});
  Markmap.create('#mindmap', undefined, root);
}})({{...window.markmap}});
</script>
</body>
</html>
"""
    return html_template

# --- Streamlit UI ---

def main():
    st.set_page_config(page_title="UPSC Mind Map Generator", layout="wide")

    st.title("UPSC Content to Mind Map Generator 🧠")
    st.markdown(
        "**Persona:** UPSC Exam Analyst | **Objective:** Convert YouTube academic content into structured, interactive mind maps for efficient revision."
    )

    with st.sidebar:
        st.header("🔑 API Configuration")
        api_key = st.text_input("Enter your Google AI API Key", type="password")
        st.markdown(
            "[Get your Google AI API key here](https://makersuite.google.com/)"
        )

    st.header("1. Input Video Details")
    video_topic = st.text_input(
        "**Video Topic (will be the title of the mind map)**",
        placeholder="e.g., 'Analysis of the Preamble of the Indian Constitution'"
    )
    youtube_url = st.text_input(
        "**YouTube Video URL**",
        placeholder="e.g., 'https://www.youtube.com/watch?v=your_video_id_here'"
    )

    if st.button("Generate Mind Map", type="primary"):
        if not api_key:
            st.error("❌ Please enter your Google AI API Key in the sidebar.")
        elif not video_topic:
            st.error("❌ Please provide a video topic.")
        elif not youtube_url:
            st.error("❌ Please provide a YouTube URL.")
        else:
            # Step 1: Extract Transcript
            with st.spinner("Step 1/3: Extracting transcript from YouTube..."):
                transcript, error = get_youtube_transcript(youtube_url)
            
            if error:
                st.error(error)
                return
            
            st.success("✅ Transcript extracted successfully!")

            # Step 2: Analyze and Generate Markdown
            with st.spinner("Step 2/3: Analyzing transcript with AI to generate mind map... (This may take a moment)"):
                markdown_output, error = generate_mind_map_markdown(api_key, video_topic, transcript)

            if error:
                st.error(error)
                return

            st.success("✅ Mind map generated successfully!")

            # Step 3: Create HTML and provide download
            with st.spinner("Step 3/3: Creating downloadable HTML file..."):
                html_content = create_markmap_html(video_topic, markdown_output)
                # Sanitize the video topic to create a valid filename
                safe_filename = re.sub(r'[\W_]+', '_', video_topic).lower() + ".html"
            
            st.success("✅ HTML file ready for download!")

            st.header("2. Review and Download")
            st.subheader("Generated Markmap Markdown")
            st.code(markdown_output, language="markdown")
            
            st.download_button(
                label="⬇️ Download Interactive Mind Map (HTML)",
                data=html_content,
                file_name=safe_filename,
                mime="text/html",
            )

if __name__ == "__main__":
    main()
