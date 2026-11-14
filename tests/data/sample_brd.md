# TEST FIXTURE: Business Requirements Document, Harbor Library Loans

This file is a fixture for the RAG tests. The product, the numbers and the rules below are invented.

## 1. Purpose
Harbor Library wants members to borrow, renew and reserve books through a website instead of at the front desk.

## 2. Scope
### 2.1 In scope
Member sign-up, catalogue search, borrowing, renewal, reservations, overdue reminders and fine payment.
### 2.2 Out of scope
Inter-library loans, e-book streaming and the staff scheduling system.

## 3. Members
### 3.1 Registration
A person registers with a library card number and a verified email address. Cards that are blocked cannot register.
### 3.2 Membership tiers
Standard members may hold 5 loans at a time. Premium members may hold 12 loans at a time.

## 4. Borrowing
### 4.1 Loan period
A standard loan lasts 21 days. A loan of a DVD lasts 7 days.
### 4.2 Renewals
A member may renew a loan up to 2 times, each renewal adds 14 days. A loan with an active reservation by another member cannot be renewed.
### 4.3 Loan limit
When a member is at the loan limit the system refuses a new loan and shows the message "Loan limit reached".

## 5. Reservations
### 5.1 Placing a reservation
A member can reserve a title that has no copy on the shelf. The queue is first come, first served.
### 5.2 Pickup window
A reserved copy is held for 5 days after the pickup email is sent. After that the copy goes to the next member in the queue.

## 6. Fines
### 6.1 Daily rate
The overdue fine is 0.25 euro per day for books and 1.00 euro per day for DVDs.
### 6.2 Fine cap
A fine for one loan never exceeds 20 euro.
### 6.3 Borrowing block
A member with unpaid fines above 10 euro cannot borrow until the fines are paid.

## 7. Payments
Fines are paid by card through the payment provider Paystream. The library never stores card numbers. A receipt is emailed within 1 minute of a successful payment.

## 8. Notifications
### 8.1 Overdue reminders
A reminder email is sent 3 days before the due date and again on the day after the due date.
### 8.2 Quiet hours
No email is sent between 22:00 and 07:00 library time.

## 9. Catalogue search
Search returns results in under 2 seconds for 95 percent of queries. A search matches title, author and ISBN. Results show whether a copy is on the shelf.

## 10. Accessibility
Every page meets WCAG 2.1 level AA and works with a screen reader.

## 11. Security
Passwords need at least 12 characters. After 5 failed sign-in attempts the account is locked for 15 minutes. Sessions end after 30 minutes without activity.

## 12. Availability
The website is available 99.5 percent of each month, excluding planned maintenance on Sundays from 02:00 to 04:00.

## 13. Data retention
Loan history is kept for 24 months after the loan is returned. Then it is anonymised and the member link is removed.

## 14. Reporting
Library managers can download a monthly report of loans, overdue items and fines collected, as a CSV file.

## 15. Open questions
Whether children under 13 may register without a parent is not decided.
