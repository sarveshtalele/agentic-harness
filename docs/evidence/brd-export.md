# Business Requirements Document (BRD)

**Project Name:** Customer Refund System - Partial Refunds
**Document Version:** 1.0
**Author:** Business Analyst
**Date:** [DD-MM-YYYY]
**Status:** Draft

## 1. Executive Summary
The purpose of this project is to enable customers to request partial refunds for specific items within an order, within a 30-day window from the original purchase. The business problem is that the current system does not support partial refunds, requiring customers to return entire orders even when only certain items are problematic. The expected outcome is a streamlined, automated refund process that allows customers to keep desired items while receiving refunds for returned items, with no manual finance approval required within the 30-day period.

## 2. Business Objectives
| ID | Objective | Success Metric | Target |
|---|---|---|---|
| BO-001 | Enable customers to refund specific items within an order | Percentage of orders with partial refunds processed | 10% (proposed) |
| BO-002 | Reduce manual approval overhead for refunds | Percentage of partial refunds auto-approved | 100% (proposed) |
| BO-003 | Improve customer satisfaction with refund process | Customer satisfaction score for refund process | 4.5 out of 5 (proposed) |

## 3. Scope

**In Scope**
- Customer ability to select specific items from an order for refund
- Partial refund processing within 30 calendar days of order date
- Auto-approval of all partial refunds within 30 calendar days, regardless of amount
- Refund amount limited to sum of prices of selected returned items, sourced from the original order record
- For bundled/promotional items (e.g., "buy one get one free"), the refund price shall be the proportion of the bundle price assigned to that item in the original order record; if no proportion is recorded, the item's refund price is zero (proposed)
- Refund eligibility of remaining items preserved when a partial refund is processed

**Out of Scope**
- Refund requests after 30 calendar days from order date (refused)
- Finance approval routing for refunds above 500 EUR (proposed deviation from initial brief; all refunds auto-approved within 30 days)
- Partial refunds for non-item-based amounts (e.g., shipping fees, taxes)
- Refund of digital or consumable items

## 4. Stakeholders
| Stakeholder / Role | Responsibility | Expectations |
|---|---|---|
| Customer | Request partial refund for specific items | Simple, fast, automated refund process with clear eligibility and amount calculation |
| Finance Team | Approve refunds (future state if policy changes) | No involvement currently; system handles automatically |
| Customer Support | Assist customers with refund issues | Clear, documented process; no manual intervention needed |
| System Administrator | Maintain refund system and monitor for abuse | Fraud detection mechanisms in place; transaction logging enabled |

## 5. Current State and Proposed State
**Current State:** Customers must return entire orders to receive a refund. No partial refund functionality exists. All refunds above 500 EUR require manual finance approval. After 30 days, refunds are refused.

**Proposed State:** Customers can select specific items within an order for refund. Within 30 calendar days of the original purchase, all partial refund requests (any amount) are auto-approved without finance routing. The refund amount is calculated as the sum of the prices of the customer-selected items, sourced from the original order record. For bundled/promotional items, the refund price shall be the proportion of the bundle price assigned to that item in the original order record; if no proportion is recorded, the item's refund price is zero (proposed). Remaining items in the order retain their refund eligibility for future partial refund requests. After 30 calendar days, all refund requests are refused.

## 6. Functional Requirements
| Requirement ID | Requirement Description | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-001 | The system shall allow a customer to select one or more individual items from an order and request a refund for only those selected items. | Must | Given an order with multiple items, when the customer selects specific items and submits a refund request, then the system initiates a partial refund process for only those selected items, and the refund request is recorded. |
| FR-002 | The system shall auto-approve all partial refund requests submitted within 30 calendar days of the original order date, regardless of the refund amount. | Must | Given a partial refund request submitted within 30 calendar days of the order, when the system processes the request, it automatically approves the refund without routing to Finance, and the refund status is set to "approved." |
| FR-003 | The system shall calculate the refund amount as the sum of the prices of the specific items the customer has selected for return, using the item prices from the original order record. For bundled/promotional items, the refund price shall be the proportion of the bundle price assigned to that item in the original order record. If no proportion is recorded, the refund price for that item shall be zero (proposed). | Must | Given a customer selects items A (50.00 EUR) and B (30.00 EUR) for refund, when the system calculates the refund amount using the prices from the original order record, then the result is exactly 80.00 EUR. Given a customer selects a "buy one get one free" item where the original order record has no assigned proportion for that item, when the system calculates the refund amount, then the refund price for that item is 0.00 EUR. |
| FR-004 | The system shall preserve the refund eligibility of all remaining items in the order after a partial refund is processed, allowing future partial refund requests for those items within the 30-day window. | Must | Given an order with items A, B, and C, when a partial refund is processed for item A, then the system shall still display items B and C as eligible for refund, and the customer can submit a new refund request for items B or C. |
| FR-005 | The system shall refuse any refund request (partial or full) submitted after 30 calendar days from the original order date, using the system's local timezone to determine the exact cutoff. | Must | Given a refund request submitted on calendar day 31 (or later) after the order date in the system's local timezone, when the system validates the date, then the system displays the error message "Refund period has expired" and refuses the request. |
| FR-006 | The system shall display to the customer, before final confirmation of the partial refund request, a summary that includes: the name and quantity of each selected item, the individual price of each selected item (from the original order record), the calculated total refund amount, and a "Confirm Refund" button. | Must | Given a customer has selected items A (50.00 EUR) and B (30.00 EUR) for refund, when the system shows the refund summary screen, then the customer sees item A at 50.00 EUR, item B at 30.00 EUR, a total refund amount of 80.00 EUR, and the "Confirm Refund" button is enabled. |

## 7. Non-Functional Requirements
| Requirement ID | Category | Requirement | Acceptance Criteria |
|---|---|---|---|
| NFR-001 | Security | The system shall ensure that only authorized customers can request refunds for their own orders. | Customer authentication required for any refund request; order ownership validated by matching customer ID before refund is processed. |
| NFR-002 | Performance | The system shall calculate the refund amount and respond to the request within 2 seconds for orders with up to 50 items. | Response time for refund calculation < 2 seconds (proposed) for orders with <= 50 items. |
| NFR-003 | Availability | The refund service shall be available during business hours (08:00 - 20:00) seven days a week. | Refund service uptime >= 99.5% (proposed) during business hours. |
| NFR-004 | Compliance | The system shall log all partial refund transactions for audit and fraud monitoring purposes. | Each partial refund generates a log entry with timestamp, customer ID, order ID, selected items, item prices (from original order record), calculated refund amount, and refund status. |

## 8. Business Rules
| Rule ID | Business Rule | Conditions / Exceptions |
|---|---|---|
| BR-001 | Refund requests are only accepted within 30 calendar days of the original order date, using the system's local timezone. The refund window closes at 23:59:59 on calendar day 30 (the exact cutoff time is based on the system's local timezone). | After day 30, requests are refused regardless of reason. The refund window starts at 00:00:00 on the order date and ends at 23:59:59 on day 30 (inclusive). |
| BR-002 | Refund amount is limited to the sum of the prices of the items the customer selects for return, sourced from the original order record. | Cannot refund more than total price of selected items. Individual item prices are taken from the original order record (the price paid by the customer at time of purchase). |
| BR-003 | For bundled/promotional items, the refund price shall be the proportion of the bundle price assigned to that item in the original order record. If no proportion is recorded, the refund price for that item shall be zero (proposed). | This rule overrides the general item price sourcing for bundled items. The system must check for proportion data in the original order record before using the default item price. |
| BR-004 | All partial refund requests are auto-approved without finance routing. | No manual approval required, regardless of refund amount. This is a proposal (proposed) that deviates from the brief's initial statement that Finance approves refunds above 500 EUR. |
| BR-005 | Remaining items retain their refund eligibility after a partial refund. | Multiple partial refunds per order are allowed within the 30-day window. The system must track which items have been refunded to prevent duplicate refunds. |

## 9. Data and Integration Requirements
| ID | Requirement | Source / Target | Description |
|---|---|---|---|
| DR-001 | The system must store per-item prices from the original order record to calculate refund amounts. | Order Management System | Retrieve item prices from the original order record (the price paid by the customer). |
| DR-002 | The system must store the original order date to enforce the 30-day refund window. | Order Management System | Compare request date against order date using system's local timezone. |
| DR-003 | The system must store proportion data for bundled/promotional items in the original order record to calculate refund amounts for those items. | Order Management System | For bundled items, store the proportion of the bundle price assigned to each item. If no proportion is recorded, the refund price defaults to zero (proposed). |
| DR-004 | The system must maintain a record of refunded items per order to track remaining eligible items. | Refund System | Track which items have been refunded to determine remaining eligibility and prevent duplicate refunds for the same item. |

## 10. Assumptions and Constraints
**Assumptions**
- The 30-day refund window is based on the original order date, not delivery date, and uses the system's local timezone for cutoff.
- Customers are authenticated and authorized to access their own orders before requesting a refund.
- The original order record contains the exact price paid by the customer for each item (including any discounts applied to that specific item).
- For bundled/promotional items, the original order record may or may not contain proportion data. If proportion data is absent, the refund price defaults to zero (proposed).

**Constraints**
- No integration with Finance approval systems; all refunds are auto-approved (proposed).
- No support for partial refunds of non-item amounts (e.g., shipping fees, taxes).
- System must comply with company refund policy and applicable consumer protection laws.

## 11. Dependencies
| ID | Dependency | Owner | Impact |
|---|---|---|---|
| DEP-001 | Access to per-item prices from Order Management System | Order Management Team | If unavailable, refund amount cannot be calculated from original order record |
| DEP-002 | Access to proportion data for bundled/promotional items from Order Management System | Order Management Team | If proportion data is unavailable, refund price defaults to zero for bundled items (proposed) |
| DEP-003 | Customer authentication and authorization service | Identity Management Team | If insecure, refunds may be processed for unauthorized users |

## 12. Risks and Mitigations
| ID | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|---|
| R-001 | Potential for abuse or fraud on high-value orders due to no finance routing (proposed) | Medium | High | Implement fraud monitoring and abuse detection with transaction logging; set transaction limits for manual review (proposed) |
| R-002 | Customers may exploit 30-day window for repeated partial refunds | Low | Medium | Track total refunded amount per order; alert on unusual patterns; max number of partial refund requests per order (proposed) – see OQ-001 |
| R-003 | Bundled/promotional items with no proportion data result in zero refund, causing customer dissatisfaction | Medium | Medium | Communicate refund policy clearly during purchase and refund process; consider business decision to assign default proportion (proposed) |

## 13. Transition Requirements
| ID | Requirement | Target Date | Owner |
|---|---|---|---|
| TR-001 | Train customer support staff on new partial refund process | [Date] | Training Team |
| TR-002 | Communicate new refund policy to customers via email and website | [Date] | Marketing Team |
| TR-003 | Deploy system updates to production | [Date] | Development Team |

## 14. Acceptance Criteria
- Customers can successfully request and receive partial refunds for specific items within 30 calendar days.
- All partial refunds within 30 calendar days are auto-approved without Finance involvement.
- Refund amount is correctly calculated as sum of selected item prices sourced from original order record.
- For bundled/promotional items, refund price uses proportion data if available; defaults to zero if not (proposed).
- Remaining items retain refund eligibility after a partial refund.
- Refund requests on or after calendar day 31 (in system's local timezone) are refused with the error message "Refund period has expired".
- Refund summary is displayed before confirmation, showing item names, individual prices, total amount, and "Confirm Refund" button.
- System logs all partial refund transactions for audit.

## 15. Requirement Traceability
| Business Objective | Requirement ID | Test Case ID | Status |
|---|---|---|---|
| BO-001 | FR-001, FR-002, FR-003, FR-005 | TC-001, TC-002 | Not Started |
| BO-002 | FR-002 | TC-003 | Not Started |
| BO-003 | FR-001, FR-006 | TC-004 | Not Started |

## 16. Open Questions
| ID | Question / Decision Required | Owner | Due Date | Status |
|---|---|---|---|---|
| OQ-001 | Should there be a maximum number of partial refund requests per order? If yes, what is the limit? | Business Owner | [Date] | Open – affects FR-004 (multiple refunds allowed) |

## 17. Approval and Sign-Off
| Stakeholder | Role | Approval Status | Date |
|---|---|---|---|
| [Name] | Business Owner | [Pending / Approved] | [Date] |
| [Name] | Project Manager | [Pending / Approved] | [Date] |
| [Name] | Technical Lead | [Pending / Approved] | [Date] |

## 18. References and Glossary

**References**
- Brief: Customers can refund part of an order within 30 days
- Questions and Answers (provided by Business Analyst)

**Glossary**
| Term | Definition |
|---|---|
| Partial Refund | A refund that covers only a subset of items in an order, allowing the customer to keep the remaining items. |
| Auto-Approval | Automatic approval of a refund request without manual finance or administrative review. |
| Refund Eligibility | The status of an item or order allowing it to be refunded within the specified window. |
| Original Order Record | The system record containing the exact prices paid by the customer for each item at the time of purchase (including any item-level discounts). |
| Bundled/Promotional Items | Items sold as part of a bundle or promotion (e.g., "buy one get one free"), where individual item prices may not be explicitly recorded. The refund price for such items uses the proportion of the bundle price assigned to that item in the original order record, or defaults to zero if no proportion is recorded (proposed). |
| Proportion Data | The portion of a bundle price assigned to each individual item within that bundle, stored in the original order record. |
| System's Local Timezone | The timezone configured for the system server, used to determine the exact cutoff for the 30-day refund window. |