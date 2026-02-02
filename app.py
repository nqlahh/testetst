import streamlit as st
import google.generativeai as genai
import streamlit.components.v1 as components
import re
from abc import ABC, abstractmethod

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================

DOC_STRUCTURE_RULES = """
You are a Professional Technical Writer. Generate a Markdown document based on the provided Python code.

STRICTLY FOLLOW THIS STRUCTURE:

1. Header Hierarchy
# Main Title (H1) - Use only ONCE at the top
## Major Sections (H2) - Main topics
### Subsections (H3) - Details under H2
#### Minor Points (H4) - Rarely needed

2. Typical Document Flow
# Title
> Brief tagline or description

## Table of Contents (for long docs)
- [Section 1](#section-1)
- [Section 2](#section-2)

## Introduction/Overview
Brief explanation of what this is about

## Main Content Sections
Organized by topic

## Examples (if applicable)
Practical demonstrations

## Conclusion/Summary
Wrap up key points

---
Footer (optional): links, credits, etc.

3. Essential Elements
- Use blank lines between paragraphs.
- Use Lists (Ordered and Unordered) for clarity.
- Use Code blocks for all code snippets.
- Use Tables for configuration or parameters.
- Use Emphasis (**bold**) for key terms.
- Keep lines under 80-100 characters when possible.
"""

# ==========================================
# DESIGN PATTERNS IMPLEMENTATION
# ==========================================

class DiagramStrategy(ABC):
    """Abstract Base Class defining the contract for diagram generators."""
    @abstractmethod
    def get_prompt(self, code_content: str) -> str:
        pass

    @abstractmethod
    def get_diagram_type_name(self) -> str:
        pass

class ClassDiagramStrategy(DiagramStrategy):
    def get_diagram_type_name(self):
        return "Class Diagram"

    def get_prompt(self, code_content):
        return f"""
        Analyze the Python code and generate a Mermaid Class Diagram.
        
        CRITICAL SYNTAX RULES (Follow strictly or the diagram will crash):
        1. Do NOT use generic types like List<Item> or Dict<Key, Value>. 
           Just write the variable name.
        2. Do NOT use square brackets [ ] for typing. 
           Mermaid uses [ ] for arrows. Using them in text will crash the renderer.
        3. Keep method signatures simple: + methodName() instead of + methodName(type: str).
        4. Look for Design Patterns (Factory, Strategy, Singleton, etc.) and label them with notes.
        
        PYTHON CODE:
        ```python
        {code_content}
        ```
        """

class ERDDiagramStrategy(DiagramStrategy):
    def get_diagram_type_name(self):
        return "ERD Diagram"

    def get_prompt(self, code_content):
        return f"""
        Analyze the Python code (specifically looking for database models, SQL, or data structures) 
        and generate a Mermaid Entity Relationship Diagram (erDiagram).
        If no database logic exists, explain why.

        PYTHON CODE:
        ```python
        {code_content}
        ```
        """

class UseCaseDiagramStrategy(DiagramStrategy):
    def get_diagram_type_name(self):
        return "Use Case Diagram"

    def get_prompt(self, code_content):
        return f"""
        Analyze the Python code to understand its functionality and actors.
        Generate a Mermaid Flowchart (TD) representing the Use Cases.
        Format: Actor -> [Action] -> System.

        PYTHON CODE:
        ```python
        {code_content}
        ```
        """

class DiagramFactory:
    """Factory to select the correct diagram strategy based on user selection."""
    @staticmethod
    def create_generator(selection: str) -> DiagramStrategy:
        if "Class" in selection:
            return ClassDiagramStrategy()
        elif "ERD" in selection:
            return ERDDiagramStrategy()
        elif "Use Case" in selection:
            return UseCaseDiagramStrategy()
        else:
            return ClassDiagramStrategy() # Default

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def sanitize_mermaid_code(code):
    """
    Removes Mermaid syntax-breaking characters from generated code.
    Focuses on removing Type Hints (e.g. : int, List<>).
    """
    lines = code.split('\n')
    cleaned_lines = []
    for line in lines:
        # 1. Remove type hints after colons (e.g. ": int", ": List[str]")
        line = re.sub(r':\s*\w+(?:<[^>]*>)?', '', line)
        
        # 2. Remove any remaining < > brackets used for generics (e.g. List<Item>)
        line = line.replace('<', '').replace('>', '')
        
        # 3. Remove square brackets [] used for lists in text (not arrows)
        # Heuristic: Only remove [ if the line is NOT a relationship line (--|>, -->, etc)
        if '--' not in line and '..' not in line and '|' not in line:
            line = line.replace('[', '').replace(']', '')
            
        cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)

# ==========================================
# STREAMLIT APP UI
# ==========================================

st.set_page_config(page_title="Python Code Analyzer", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Enter your Gemini API Key", type="password")
    st.markdown("---")
    st.info("**Architecture:** Uses Factory & Strategy patterns for robust diagram generation.")

if not api_key:
    st.warning("Please enter your API Key in the sidebar.")
    st.stop()

# Configure API
genai.configure(api_key=api_key)

# --- FILE UPLOAD ---
st.header("📄 Upload Python Code")
uploaded_file = st.file_uploader("Choose a .py file", type=['py'])

code_content = ""
if uploaded_file is not None:
    code_content = uploaded_file.read().decode("utf-8")
    with st.expander("View Uploaded Code", expanded=False):
        st.code(code_content, language='python')

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["💬 Chat", "📝 Documentation", "📊 Diagrams"])

# ==========================
# TAB 1: CHAT
# ==========================
with tab1:
    st.header("Chat with Code")
    if "messages" not in st.session_state: 
        st.session_state.messages = []
    
    # Display History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Input
    if prompt := st.chat_input("Ask a question about the code..."):
        if code_content:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            model = genai.GenerativeModel(model_name="gemini-2.5-flash-lite")
            response = model.generate_content(f"Code: {code_content}\nQ: {prompt}")
            
            with st.chat_message("assistant"):
                st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})

# ==========================
# TAB 2: DOCUMENTATION (UPDATED AS REQUESTED)
# ==========================
with tab2:
    st.header("Documentation Generator")
    st.write("Click the button below to auto-generate a README.md file based on the code structure.")
    
    # Button to trigger generation
    if st.button("🚀 Generate Documentation", type="primary"):
        if not code_content:
            st.error("Please upload a Python file first!")
        else:
            with st.spinner("Analyzing code and writing documentation..."):
                # Initialize a fresh model for Doc generation (clean slate)
                model_doc = genai.GenerativeModel(model_name="gemini-2.5-flash-lite")
                
                # Combine rules + code
                doc_prompt = f"{DOC_STRUCTURE_RULES}\n\nPYTHON CODE TO DOCUMENT:\n```python\n{code_content}\n```"
                
                response = model_doc.generate_content(doc_prompt)
                markdown_output = response.text
                
                # Display result
                st.markdown("---")
                st.markdown("### Generated Documentation Preview:")
                st.markdown(markdown_output)
                
                # Provide a download button
                st.download_button(
                    label="📥 Download README.md",
                    data=markdown_output,
                    file_name="README.md",
                    mime="text/markdown"
                )

# ==========================
# TAB 3: DIAGRAMS
# ==========================
with tab3:
    st.header("Generate Diagrams")
    
    if not code_content:
        st.info("👈 Please upload a Python file to generate diagrams.")
    else:
        # Controls
        col_select, col_btn = st.columns([2, 1])
        
        with col_select:
            diagram_selection = st.selectbox(
                "Choose Diagram Type",
                ("Class Diagram (Check for Patterns)", "ERD Diagram", "Use Case Diagram")
            )
        
        with col_btn:
            st.write("") 
            st.write("") 
            generate_clicked = st.button("🎨 Generate", type="primary", use_container_width=True)

        # Generator Logic
        if generate_clicked:
            col_code, col_diagram = st.columns(2)

            # Left Column: Source Code Preview
            with col_code:
                st.subheader("📂 Source Code Preview")
                st.code(code_content, language='python', line_numbers=True, height=700)
            
            # Right Column: Diagram Visualization
            with col_diagram:
                st.subheader("📊 Diagram Preview")
                
                with st.spinner("Analyzing code structure..."):
                    # 1. Use Factory to get strategy
                    generator_strategy = DiagramFactory.create_generator(diagram_selection)
                    prompt = generator_strategy.get_prompt(code_content)
                    
                    # 2. Call AI
                    model = genai.GenerativeModel(model_name="gemini-2.5-flash-lite")
                    response = model.generate_content(prompt)
                    output_text = response.text

                # 3. Extract Mermaid Code
                pattern = r"```(?:mermaid|flowchart|classDiagram|erDiagram)(.*?)```"
                matches = re.findall(pattern, output_text, re.DOTALL)
                raw_mermaid = matches[0].strip() if matches else ""

                if raw_mermaid:
                    # 4. Debug View (Hidden by default)
                    with st.expander("🐞 Debug View (Raw Code)", expanded=False):
                        st.code(raw_mermaid, language="markdown")

                    # 5. Sanitize Code (Fix Syntax Errors)
                    clean_mermaid = sanitize_mermaid_code(raw_mermaid)

                    # 6. Render HTML Injection
                    html_template = f"""
                    <div style="width: 100%; overflow: auto; display: flex; justify-content: center;">
                        <pre class="mermaid">
                        {clean_mermaid}
                        </pre>
                    </div>
                    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.0/dist/mermaid.min.js"></script>
                    <script>
                        mermaid.initialize({{
                            startOnLoad: true,
                            theme: 'default',
                            securityLevel: 'loose'
                        }});
                    </script>
                    """
                    
                    st.success("Rendering diagram...")
                    components.html(html_template, height=600, scrolling=False)
                else:
                    st.error("❌ Could not extract diagram code from AI response.")
