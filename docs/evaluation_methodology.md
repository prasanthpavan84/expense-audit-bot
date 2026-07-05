# Evaluation Methodology

This document outlines the detailed scoring criteria, evaluation parameters, and analysis principles.

## 1. Weighted Scorecard Criteria
The system computes the **Overall AI Score** using a weighted average of performance across isolated evaluation categories:
* **OCR accuracy**: 20%
* **Policy Compliance**: 40%
* **Security Protection**: 20%
* **Overall Decision Accuracy**: 20%

## 2. Statistical Analysis Rules
* **Confidence Intervals**: Computed for latency metrics using a Z-score of 1.96 for a 95% confidence level.
* **Confusion Matrix**: Maps cases into True Positives, False Positives, False Negatives, and True Negatives to derive Precision, Recall, and F1 values.
