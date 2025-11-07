#ReviewR Database
Here is some info about our database and its relations
 writer/reviewer information  
- Paper: research papers uploaded by users  
- Review: feedback from reviewers on papers  
- Company: linked companies for valorisation  
- PaperCompany: junction table for N–M relationship  

Relationships
- User 1 → N Paper  
- User 1 → N Review  
- Paper 1 → N Review  
- Paper N → M Company (via PaperCompany)
