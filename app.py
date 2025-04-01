import streamlit as st
import pandas as pd
import yaml
import re
from io import BytesIO
from datetime import datetime
import os

# --- Load rules from YAML file ---
def load_rules():
    with open("rules.yaml", "r") as f:
        return yaml.safe_load(f)

# --- Save updated rules to YAML ---
def save_rules(rules):
    with open("rules.yaml", "w") as f:
        yaml.dump(rules, f)

# --- Log changes to rules for version control ---
def log_rule_changes(changes):
    log_entry = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n" + "\n".join(changes) + "\n"
    with open("rule_change_log.txt", "a") as log_file:
        log_file.write(log_entry)

# --- Normalize and classify ---
def normalize_text(text):
    if pd.isna(text):
        return ""
    return re.sub(r"[^\w\s]", " ", str(text).lower())

def classify_row(row, rules):
    text = " ".join([
        normalize_text(row.get("Type")),
        normalize_text(row.get("Description")),
        normalize_text(row.get("Model"))
    ])

    if any(h in text for h in rules["ignore_if_contains"]):
        return "Ignore"
    if any(kw in text for kw in rules["active_keywords"]):
        return "Active"
    if any(kw in text for kw in rules["passive_keywords"]):
        return "Passive"
    return "Unclassified"

# --- Main App ---
st.title("📦 iBwave BOM Classifier")

st.markdown("Upload your iBwave Excel BOM and classify components into Active or Passive.")

uploaded_file = st.file_uploader("Upload iBwave BOM Excel file", type=["xlsx"])

if uploaded_file:
    rules = load_rules()
    df = pd.read_excel(uploaded_file, skiprows=10)
    df = df.dropna(how="all")

    # Apply classification
    df["Classification"] = df.apply(lambda row: classify_row(row, rules), axis=1)

    st.success("Classification complete!")
    st.dataframe(df.head(50))

    # Feedback section
    st.markdown("### 🛠️ Corrections")
    st.markdown("If you see any misclassifications, correct them below:")
    df["Correct Classification"] = df["Classification"]
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

    if st.button("🔁 Update Rules from Corrections"):
        changes_log = []
        for _, row in edited_df.iterrows():
            if row["Classification"] != row["Correct Classification"]:
                text = " ".join([
                    normalize_text(row.get("Type")),
                    normalize_text(row.get("Description")),
                    normalize_text(row.get("Model"))
                ])
                keyword = text.split()[0] if text.split() else ""
                if row["Correct Classification"] == "Active" and keyword not in rules["active_keywords"]:
                    rules["active_keywords"].append(keyword)
                    changes_log.append(f"Added '{keyword}' to active_keywords")
                elif row["Correct Classification"] == "Passive" and keyword not in rules["passive_keywords"]:
                    rules["passive_keywords"].append(keyword)
                    changes_log.append(f"Added '{keyword}' to passive_keywords")

        # Remove duplicates
        rules["active_keywords"] = list(set(rules["active_keywords"]))
        rules["passive_keywords"] = list(set(rules["passive_keywords"]))

        # Save updated rules and log
        save_rules(rules)
        if changes_log:
            log_rule_changes(changes_log)
        st.success("Rules updated based on corrections! Changes logged.")

    # Option to download
    output = BytesIO()
    edited_df.to_excel(output, index=False)
    st.download_button(
        label="📥 Download Classified BOM",
        data=output.getvalue(),
        file_name="classified_bom.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
