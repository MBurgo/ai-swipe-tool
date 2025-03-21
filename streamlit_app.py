import streamlit as st
from openai import OpenAI
import pdfplumber
import email
from bs4 import BeautifulSoup
import extract_msg

# Securely load API key from Streamlit secrets
client = OpenAI(api_key=st.secrets["openai"]["api_key"])

# --- Streamlit UI ---
st.set_page_config(page_title="Burgo's 'Swipe and Fool' Tool")
st.title("📬 Burgo's 'Swipe and Fool' Tool")

st.markdown("""
<div style="background-color:#f0f2f6;padding:16px;border-radius:8px;margin-bottom:16px;">
<h4>ℹ️ About This Tool</h4>
<p>Have you ever received an email, or seen an ad, and thought, "Oooh, I know this ad is actually for dog food, but maybe we could do something similar"?</p>
<p>This tool helps you adapt marketing assets from other industries or businesses into something that could work for The Motley Fool Australia.</p>
<p><strong>Important:</strong> This is not a magic button that gives you a perfect email, ad, or landing page. Think of it as a <strong>conceptual transposer</strong> — it pulls across structure, tactics, and tone, then reworks them for our products and audience.</p>
<p>What you’ll get is a <strong>starting point</strong> — a rewritten version in our voice, aimed at our readers. It might be rough. It might even miss the mark. But it should give you a workable shell or idea to refine further.</p>
<h5>What to do:</h5>
<ul>
  <li>You can either upload a .eml, .msg or .pdf file below, or just copy and paste in your source asset text (email, ad, landing page, etc.)</li>
  <li>Choose the Motley Fool product</li>
  <li>(Optional) Describe your target persona</li>
</ul>
<p>The tool will return a <strong>Foolishified</strong> version of the copy, plus a short breakdown of <strong>why the tactic works</strong>.</p>
</div>
""", unsafe_allow_html=True)

# File Upload (optional)
uploaded_file = st.file_uploader("Upload a PDF, .eml, or .msg file (optional)", type=["pdf", "eml", "msg"])
extracted_text = ""

if uploaded_file:
    try:
        if uploaded_file.type == "application/pdf":
            with pdfplumber.open(uploaded_file) as pdf:
                extracted_text = "\n".join(
                    page.extract_text() for page in pdf.pages if page.extract_text()
                )
        elif uploaded_file.name.endswith(".eml"):
            raw_bytes = uploaded_file.read()
            msg = email.message_from_bytes(raw_bytes)

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))

                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
                    elif content_type == "text/html" and "attachment" not in content_disposition:
                        html_body = part.get_payload(decode=True).decode(errors="ignore")
                        soup = BeautifulSoup(html_body, "html.parser")
                        body = soup.get_text()
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

            extracted_text = body.strip()
        elif uploaded_file.name.endswith(".msg"):
            msg = extract_msg.Message(uploaded_file)
            msg.encoding = 'utf-8'
            extracted_text = msg.body.strip()
        else:
            st.error("Unsupported file type.")
    except Exception as e:
        st.error(f"Error processing file: {e}")

# Input Method (pre-populate from upload if available)
source_email = st.text_area(
    "Paste the source marketing asset copy below:",
    value=extracted_text,
    height=300
)

# Asset Type Selector
asset_type = st.selectbox(
    "What type of asset are you adapting?",
    ["Email", "Ad", "Landing/Order Page", "Social Post", "Other"]
)

# Product Selector
product = st.selectbox("Select Motley Fool product:", ["Share Advisor", "Dividend Investor", "Extreme Opportunities"])

# Persona Input (Optional)
persona = st.text_input("Describe your target persona (optional):", placeholder="e.g., Retiree, side hustler, beginner investor")

# Button to generate output
if st.button("Generate Motley Fool Version"):
    if not source_email.strip():
        st.warning("Please paste a source asset to proceed.")
    else:
        # Build prompt
        source = source_email.strip()

        prompt = (
            f"You are a marketing strategist for The Motley Fool Australia.\n\n"
            f"A marketer has submitted a successful {asset_type.lower()} from another business "
            f"(e.g., dog food, travel). Your job is to extract the structure, persuasive tactics, and tone, "
            f"and then rewrite a version of it that sells a Motley Fool product in a way that aligns with Fool Australia's tone "
            f"(plainspoken, honest, educational, slightly cheeky, optimistic).\n\n"
            f"Product: {product}\n"
            f"Persona: {persona if persona else 'General audience'}\n\n"
            f"Source {asset_type}:\n\"\"\"\n{source}\n\"\"\"\n\n"
            f"---\n\n"
        )

        if asset_type == "Email":
            prompt += (
                f"Please return your output using the following format:\n\n"
                f"### Subject Line:\n<Your subject line here>\n\n"
                f"### Preview Text:\n<Your preview snippet here>\n\n"
                f"### Rewritten Motley Fool Email:\n<Your rewritten version here>\n\n"
                f"### Why This Works:\n<Brief breakdown of tactics used>"
            )
        else:
            prompt += (
                f"Please return your output using the following format:\n\n"
                f"### Rewritten Motley Fool {asset_type}:\n<Your rewritten version here>\n\n"
                f"### Why This Works:\n<Brief breakdown of tactics used>"
            )

        # Call OpenAI
        with st.spinner("Transposing the concept..."):
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a creative and strategic copywriter."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1200
            )

            output = response.choices[0].message.content

        # Display output
        if asset_type == "Email":
            subject = preview = body = reasoning = ""
            if "### Subject Line:" in output:
                parts = output.split("### Subject Line:")[1].split("### Preview Text:")
                subject = parts[0].strip()
                if "### Rewritten Motley Fool Email:" in output:
                    preview, remainder = output.split("### Preview Text:")[1].split("### Rewritten Motley Fool Email:")
                    preview = preview.strip()
                    if "### Why This Works:" in remainder:
                        body, reasoning = remainder.split("### Why This Works:")
                        body = body.strip()
                        reasoning = reasoning.strip()
                    else:
                        body = remainder.strip()

            st.subheader("📨 Subject Line")
            st.markdown(subject)

            st.subheader("🔍 Preview Text")
            st.markdown(preview)

            st.subheader("✍️ Rewritten Motley Fool Email")
            st.markdown(body)

            if reasoning:
                st.subheader("🧠 Why This Works")
                st.markdown(reasoning)

        else:
            rewritten = ""
            reasoning = ""

            if f"### Rewritten Motley Fool {asset_type}:" in output:
                parts = output.split(f"### Rewritten Motley Fool {asset_type}:")[1].split("### Why This Works:")
                rewritten = parts[0].strip()
                reasoning = parts[1].strip() if len(parts) > 1 else ""

            st.subheader(f"✍️ Rewritten Motley Fool {asset_type}")
            st.markdown(rewritten)

            if reasoning:
                st.subheader("🧠 Why This Works")
                st.markdown(reasoning)
