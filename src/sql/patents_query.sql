SELECT p.publication_number, p.application_number, p.filing_date, p.country_code, a.name AS assignee,
  (SELECT LOGICAL_OR(c.code LIKE 'G06N%') FROM UNNEST(p.cpc) c) AS cpc_g06n,
  (SELECT STRING_AGG(t.text, ' ') FROM UNNEST(p.title_localized) t WHERE t.language = 'en') AS title,
  (SELECT STRING_AGG(x.text, ' ') FROM UNNEST(p.abstract_localized) x WHERE x.language = 'en') AS abstract
FROM `patents-public-data.patents.publications` p, UNNEST(p.assignee_harmonized) a
WHERE REGEXP_CONTAINS(UPPER(a.name), r'(^STATE BANK OF INDIA)|(^BANK OF BARODA)|(^PUNJAB NATIONAL BANK)|(^CANARA BANK)|(^UNION BANK OF INDIA)|(^BANK OF INDIA)|(^INDIAN BANK( LTD| LIMITED)?$)|(^CENTRAL BANK OF INDIA)|(^INDIAN OVERSEAS BANK)|(^UCO BANK)|(^BANK OF MAHARASHTRA)|(^PUNJAB (AND|&) SIND BANK)|(^HDFC BANK)|(^ICICI BANK)|(^AXIS BANK)|(^KOTAK MAHINDRA BANK)|(^INDUSIND BANK)|(^(THE )?FEDERAL BANK( LTD| LIMITED)?$)|(^YES BANK)|(^(RBL BANK|RATNAKAR BANK))|(^(THE )?KARUR VYSYA BANK)|(^CITY UNION BANK)|(^(THE )?SOUTH INDIAN BANK)|(^(DCB BANK|DEVELOPMENT CREDIT BANK))|(^IDFC (FIRST )?BANK)') AND p.filing_date >= 20090401
