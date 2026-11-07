
def detect_business_domain(df):
    """Infer the likely business domain from dataset column names."""

    columns = [str(col).lower().replace("_", " ") for col in df.columns]

    domain_keywords = {
        "Sales and Retail": [
            "sales", "purchase", "revenue", "product",
            "order", "quantity", "price", "profit",
            "discount", "store"
        ],
        "Loan and Credit Risk": [
            "loan", "credit", "default", "interest",
            "borrower", "emi", "debt", "approval",
            "income", "delinquency"
        ],
        "Marketing": [
            "campaign", "marketing", "conversion",
            "impression", "click", "lead", "ad spend",
            "acquisition", "engagement"
        ],
        "Customer Analytics": [
            "customer", "client", "churn", "retention",
            "satisfaction", "lifetime value", "segment"
        ],
        "Human Resources": [
            "employee", "salary", "department",
            "attrition", "tenure", "performance",
            "joining date", "designation"
        ],
        "Finance": [
            "expense", "cost", "balance", "cash flow",
            "budget", "investment", "asset", "liability"
        ]
    }

    scores = {}

    for domain, keywords in domain_keywords.items():
        score = 0

        for column in columns:
            for keyword in keywords:
                if keyword in column:
                    score += 1

        scores[domain] = score

    best_domain = max(scores, key=scores.get)
    best_score = scores[best_domain]

    if best_score == 0:
        return {
            "domain": "General Business Analytics",
            "confidence": "Low",
            "evidence": [],
            "domain_scores": scores
        }

    matched_keywords = [
        keyword
        for keyword in domain_keywords[best_domain]
        if any(keyword in column for column in columns)
    ]

    # Confidence is an indicative heuristic, not a statistical probability.
    if best_score >= 4:
        confidence = "High"
    elif best_score >= 2:
        confidence = "Medium"
    else:
        confidence = "Low"

    return {
        "domain": best_domain,
        "confidence": confidence,
        "evidence": matched_keywords,
        "domain_scores": scores
    }


def create_analysis_plan(df, domain_result):
    """Create an initial business analysis plan automatically."""

    domain = domain_result["domain"]

    columns = {
        str(col).lower().replace("_", " "): str(col)
        for col in df.columns
    }

    plans = {
        "Sales and Retail": [
            {
                "analysis": "Revenue and sales performance",
                "purpose": "Understand overall sales performance.",
                "keywords": ["sales", "revenue", "purchase amount", "amount"]
            },
            {
                "analysis": "Sales trends over time",
                "purpose": "Identify growth, declines and seasonal patterns.",
                "keywords": ["date", "order date", "purchase date", "month"]
            },
            {
                "analysis": "Geographical performance",
                "purpose": "Compare business performance across locations.",
                "keywords": ["city", "region", "state", "country"]
            },
            {
                "analysis": "Product performance",
                "purpose": "Identify products contributing to business results.",
                "keywords": ["product", "category", "item"]
            },
            {
                "analysis": "Customer behaviour",
                "purpose": "Understand customer purchasing patterns.",
                "keywords": ["customer", "customer id", "age", "segment"]
            }
        ],

        "Loan and Credit Risk": [
            {
                "analysis": "Loan approval and rejection patterns",
                "purpose": "Understand lending approval outcomes.",
                "keywords": ["loan status", "approval", "loan"]
            },
            {
                "analysis": "Default risk analysis",
                "purpose": "Identify patterns associated with loan defaults.",
                "keywords": ["default", "loan status", "delinquency"]
            },
            {
                "analysis": "Borrower financial profile",
                "purpose": "Study income, debt and repayment capacity.",
                "keywords": ["income", "debt", "loan amount", "interest"]
            },
            {
                "analysis": "Risk segmentation",
                "purpose": "Compare risk patterns across borrower groups.",
                "keywords": ["grade", "risk", "purpose", "employment"]
            }
        ],

        "Marketing": [
            {
                "analysis": "Campaign performance",
                "purpose": "Compare the performance of marketing campaigns.",
                "keywords": ["campaign", "impression", "click"]
            },
            {
                "analysis": "Conversion analysis",
                "purpose": "Understand how effectively leads convert.",
                "keywords": ["conversion", "lead", "customer"]
            },
            {
                "analysis": "Marketing expenditure",
                "purpose": "Evaluate marketing spend against outcomes.",
                "keywords": ["spend", "cost", "budget"]
            }
        ],

        "Customer Analytics": [
            {
                "analysis": "Customer segmentation",
                "purpose": "Identify different customer groups.",
                "keywords": ["customer", "segment", "age", "city"]
            },
            {
                "analysis": "Customer retention and churn",
                "purpose": "Understand customer retention patterns.",
                "keywords": ["churn", "retention", "status"]
            },
            {
                "analysis": "Customer value analysis",
                "purpose": "Identify valuable customer groups.",
                "keywords": ["lifetime value", "revenue", "purchase"]
            }
        ],

        "Human Resources": [
            {
                "analysis": "Employee attrition",
                "purpose": "Understand employee exits and retention.",
                "keywords": ["attrition", "employee", "status"]
            },
            {
                "analysis": "Compensation analysis",
                "purpose": "Compare salary and compensation patterns.",
                "keywords": ["salary", "income", "compensation"]
            },
            {
                "analysis": "Workforce segmentation",
                "purpose": "Compare workforce groups and departments.",
                "keywords": ["department", "designation", "tenure"]
            }
        ],

        "Finance": [
            {
                "analysis": "Income and expense analysis",
                "purpose": "Understand financial inflows and outflows.",
                "keywords": ["income", "revenue", "expense", "cost"]
            },
            {
                "analysis": "Financial trends",
                "purpose": "Identify changes in financial performance.",
                "keywords": ["date", "month", "year"]
            },
            {
                "analysis": "Profitability analysis",
                "purpose": "Understand profit and margin patterns.",
                "keywords": ["profit", "margin", "revenue"]
            }
        ]
    }

    selected_plans = plans.get(
        domain,
        [
            {
                "analysis": "Dataset structure analysis",
                "purpose": "Understand the available data and its characteristics.",
                "keywords": []
            },
            {
                "analysis": "Numerical relationship analysis",
                "purpose": "Identify meaningful relationships between numerical fields.",
                "keywords": []
            },
            {
                "analysis": "Category comparison",
                "purpose": "Compare available business categories.",
                "keywords": []
            }
        ]
    )

    available_analyses = []

    for plan in selected_plans:
        matched_columns = []

        for keyword in plan["keywords"]:
            for normalized_name, original_name in columns.items():
                if keyword in normalized_name:
                    if original_name not in matched_columns:
                        matched_columns.append(original_name)

        # Keep an analysis only when the dataset has relevant columns.
        if matched_columns:
            available_analyses.append({
                "analysis": plan["analysis"],
                "purpose": plan["purpose"],
                "relevant_columns": matched_columns
            })

    return available_analyses


def analyze_business_context(df):
    """Run domain detection and create an automatic analysis plan."""

    domain_result = detect_business_domain(df)

    analysis_plan = create_analysis_plan(df, domain_result)

    return {
        "business_domain": domain_result,
        "analysis_plan": analysis_plan
    }
