from sentence_transformers import SentenceTransformer, util
from sklearn.feature_extraction.text import TfidfVectorizer
from keybert import KeyBERT
import spacy
import nltk
import pandas as pd
# 匯入 os 模組處理檔案與路徑
import os
import requests
import torch  # ✅ 新增 torch 匯入以支援相似度比對
import time
# # ---------- 載入模型 ----------
# # 檢查模型是否已存在，否則自動下載並儲存
# model_path = './models/paraphrase-MiniLM-L6-v2'
# if not os.path.exists(model_path):
#     print("📥 正在下載模型並儲存到本地...")
#     model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
#     model.save(model_path)
# else:
#     print("✅ 已找到本地模型，直接載入")
# 初始化模型
# ========== 🔍 啟動時間計時器 ==========
t_start = time.time()
print("🔥 啟動時間診斷中...")

# ========== ✅ 載入語意模型 ==========
t_model_load = time.time()
bert_model = SentenceTransformer('./models/paraphrase-MiniLM-L6-v2')
print(f"📦 BERT 模型載入完成，用時：{time.time() - t_model_load:.2f} 秒")

# ========== ✅ 初始化 KeyBERT ==========
t_keybert = time.time()
keybert_model = KeyBERT(bert_model)
print(f"🧠 KeyBERT 初始化完成，用時：{time.time() - t_keybert:.2f} 秒")

# ========== ✅ 載入 spaCy 模型 ==========
t_spacy = time.time()
nlp = spacy.load("en_core_web_sm")
print(f"🧬 spaCy 模型載入完成，用時：{time.time() - t_spacy:.2f} 秒")

t_nltk = time.time()
nltk.download('punkt')
nltk.download('stopwords')


print(f"📚 NLTK 初始化完成，用時：{time.time() - t_nltk:.2f} 秒")

# ========== ✅ 總結 ==========
print(f"🚀 模型初始化總耗時：約 {time.time() - t_start:.2f} 秒")

# 高風險語句樣本
high_risk_examples = [
    'cannot sign in', 'login failed', 'unable to login', 'access denied',
    'offline', 'not pingable', 'disconnect', 'network error',
    'disabled by admin', 'environment creation blocked',
    'blocked by conditional access',
    'error', 'failed', 'crash', 'freeze', 'hang', 'exception',
    '登入失敗', '封鎖', '權限不足', '連線失敗', '無法連線', '故障', '卡住', 'locked out',     
    "device must comply with your organization's compliance requirements",
    "your device does not meet your organization's compliance requirements",
    "unable to authenticate sign-in",
    "certificate validation failed",
    "access has been blocked by Conditional Access policies",
    "user is not able to access MS resources",
    "device disabled unable to access resources",
    "you can't get there from here",
    "login need to change password",
    "windows login prompt error message",
    "alias changed, computer cannot log in",
    "bitlocker is locked",
    "PIN code cannot be turned on",
    "can't login to Teams and Outlook",
    "device is lost",
    "device deleted",
    "new device enroll successful but cannot login",
    "unable to access company resources",
    "surface laptop cannot be turned on",
    "laptop freeze after opening excel",
    "cannot boot",
    "windows installation encountered an unexpected error",
    "black screen and unable to power on",
    "sync with Microsoft Defender for Endpoint",
    "certificate verification failure",
    "unable to verify account",
    "unable to receive 2-digit push MFA",
    "access to your account has been temporarily restricted",
    "authorization login issue",
    "Microsoft Defender not syncing",
    "Onenote data is lost after alias is changed",
    "error loading control",
    "Teams cannot be used properly",
    "output file error",
    "error code: 0x80070057",
    "financial posting failed",
    "submitted report not reflecting",
    "unable to access SharePoint",
    "404 file not found",
    "mailbox won't open",
    "projector won't turn on",
    "no display from HDMI",
    "The user is completely blocked from accessing Microsoft resources.",
    "Device does not comply with organization security requirements.",
    "BitLocker is locked, user is locked out.",
    "Unable to authenticate with MFA, access denied.",
    "System login failure after password reset.",
    "Laptop can't boot, black screen shows on startup.",
    "Important file or data is missing after account change.",
    "Microsoft Defender failed to sync, device marked non-compliant.",
    "Critical application crash leads to data loss.",
    "Account disabled, unable to sign in.",
]
high_risk_embeddings = bert_model.encode(high_risk_examples, convert_to_tensor=True)

# 升級處理語句樣本
escalation_examples = [
    'escalation approved', 'escalated', 'escalate to', 
    'SME', 'senior engineer', 'escalation path',
    'Rashdan Ismail', "Issue has been escalated to the engineering team.",
    "This case was re-elevated for further analysis.",
    "Escalated to T3 support for resolution.",
    "Transferred the ticket to the compliance team.",
    "Bug was resolved after escalation.",
    "Multiple teams have been engaged for investigation.",
    "Dispatched ICM for escalation.",
    "The issue has been linked to a master incident.",
    "Escalation path has been triggered.",
    "SME provided final confirmation after escalation.",
        "elevated to engineering team",
    "escalated to T3 support",
    "elevated to Multi Year Pricing Portal",
    "re-elevated with the caller's latest response",
    "escalated to Service Operations Team via IcM",
    "connected with user over MS Teams",
    "escalated to Broker Partner Authorization Team",
    "mitigated by turning off the flight",
    "engaged multiple teams",
    "compliance team undeployed a few compliance services",
    "engineering team fixed",
    "engineering team resolved the bug",
    "SME mentioned that",
    "dispatched ICM for further assistance",
    "added to exception list with help of admin",
    "called profiling team",
    "reimaged MTR using ZTN image",
    "rejoined MS domain",
    "bug has been fixed",
    "ticket elevated",
    "bug in database system",
    "ICM dispatched",
    "transferred to specialized team",
    "user request forwarded",
    "final mitigation",
    "compliance issue escalated",
    "multiple teams were engaged",
    "DRI team provided updates",
    "master incident",
    "linked to the parent incident",
    "confirmed by engineering",
    "added to global allowlist",
    
]
escalation_embeddings = bert_model.encode(escalation_examples, convert_to_tensor=True)

# 多人受影響語句樣本
multi_user_examples = [
    'two meeting rooms', 'multiple rooms', 'both', 'colleague and I',
    'staff', 'users', 'employees', 'team', 'group', '全體', '多人',
    "multiple users",
    "entire team",
    "all users",
    "everyone",
    "colleagues",
    "group",
    "department",
    "students",
    "our site",
    "whole office",
    "entire org",
    "more than one user",
    "several users",
    "entire class",
    "users in Taipei office",
    "multiple devices affected",
    "widespread",
    "massive impact",
    "not limited to one user",
    ]
multi_user_embeddings = bert_model.encode(multi_user_examples, convert_to_tensor=True)

# ---------- 語意判斷函式 ----------

def is_high_risk(text):
    if not isinstance(text, str):  # 如果不是字串
        if pd.isna(text):          # 如果是 NaN
            text = ""
        else:
            text = str(text).strip()  # 轉成字串並移除空白

    emb = bert_model.encode(text, convert_to_tensor=True)
    score = util.cos_sim(emb, high_risk_embeddings).max().item()
    return int(score > 0.5)# 考慮降閾值


def is_escalated(text):
    if not isinstance(text, str):
        if pd.isna(text):
            text = ""
        else:
            text = str(text).strip()

    emb = bert_model.encode(text, convert_to_tensor=True)
    score = util.cos_sim(emb, escalation_embeddings).max().item()
    return int(score > 0.5)# 考慮降閾值


def is_multi_user(text):
    if not isinstance(text, str):
        if pd.isna(text):
            text = ""
        else:
            text = str(text).strip()

    emb = bert_model.encode(text, convert_to_tensor=True)
    score = util.cos_sim(emb, multi_user_embeddings).max().item()
    return int(score > 0.5)# 考慮降閾值


# ---------- 自動關鍵字抽取 ----------

def extract_keywords(text, top_n=3):
    if not isinstance(text, str):
        if pd.isna(text):
            text = ""
        else:
            text = str(text).strip()

    return [kw[0] for kw in keybert_model.extract_keywords(text, top_n=top_n)]


# ---------- 擴充：解法推薦 ----------

def recommend_solution(text):
    if not isinstance(text, str):
        if pd.isna(text):
            text = ""
        else:
            text = str(text).strip()

    lowered = text.lower()

    if "login" in lowered:
        return "Please check your username/password, SSO settings, and permissions."
    elif "network" in lowered or "connection" in lowered:
        return "Please verify your network connection, VPN settings, and DNS configuration."
    elif "crash" in lowered or "freeze" in lowered:
        return "Try restarting the system and checking the application version."
    else:
        return "Refer to similar cases or contact the support team for assistance."
    


def is_actionable_resolution(text):
    if not isinstance(text, str) or not text.strip():
        return False

    # ✅ 標準的「有提供解法」語氣樣板（可擴充）
    reference_texts = [
        "The issue was fixed by restarting the system.",
        "Steps were provided to the user.",
        "We guided the user through the process.",
        "Enabled access via admin portal.",
        "Action was completed successfully.",
        "The user's account was reactivated.",
        "Password was reset to restore access.",
        "Configuration settings were updated.",
        "Provided instructions to resolve the issue.",
        "Assisted the user remotely via Teams.",
        "Cleared cache and restarted the application.",
        "The permission issue was resolved by updating roles.",
        "Resolved by reinstalling the software.",
        "User was instructed to follow internal SOP.",
        "Helped user reset MFA settings.",
        "Added the user as a guest in the tenant.",
        "Reimaged the device to resolve the problem.",
        "VPN settings were corrected.",
        "Shared the fix through internal documentation.",
        "Confirmed the issue was resolved with user.",
        "Escalated issue was resolved by SME.",
        "Firewall rules were updated to allow access.",
        "License was reassigned to the correct user.",
        "System was patched to address the issue.",
        "Session was terminated and re-established to fix connectivity."
    ]


    try:
        # Encode 目標文字與樣板
        target_embedding = bert_model.encode(text, convert_to_tensor=True)
        reference_embeddings = bert_model.encode(reference_texts, convert_to_tensor=True)

        # 取最大語意相似度
        cosine_scores = util.cos_sim(target_embedding, reference_embeddings)
        max_score = cosine_scores.max().item()

        print(f"🧠 Resolution 類似度最高分：{max_score:.2f}")  # ✅ 可印出 debug 分數

        return max_score >= 0.5  # 門檻可調整
    except Exception as e:
        print("❌ 類似度分析錯誤：", e)
        return False

def extract_cluster_name(texts, max_features=5, top_k=2):
    """
    從一組文字中抽取代表主題的關鍵詞，用於命名 cluster。
    """
    if not texts:
        return "cluster"
    
    vectorizer = TfidfVectorizer(max_features=max_features, stop_words='english')
    X = vectorizer.fit_transform(texts)
    keywords = vectorizer.get_feature_names_out()
    return "_".join(keywords[:top_k]) if len(keywords) >= top_k else "_".join(keywords) if keywords.size > 0 else "cluster"

