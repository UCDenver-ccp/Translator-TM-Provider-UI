# Text Mining UI and Feedback

This is a basic project to query the contents of the Targeted Assertion DB. 
It was created to run out of GCP's Cloud Run and connect to a GCP SQL DB. The front end is simply an HTML file with inline JS with a bit of jQuery and Bootstrap. 

Additional endpoints have been added to display specific Assertions with all associated evidence (e.g. https://tmui.text-mining-kp.org/assertions/0000403cca20f3a46afabccdff26154151e897efb99e344fa8a2d343ff9b16a9), and specific Evidence records (e.g. https://tmui.text-mining-kp.org/evidence/00000005a0876f89396326909e5128991cf7dbc6e9649f724f6687981e6dceab) and provide feedback.
Finally, the same display and feedback functionality has been added for SemMedDB predications (e.g. https://tmui.text-mining-kp.org/semmed/predication/10612762).