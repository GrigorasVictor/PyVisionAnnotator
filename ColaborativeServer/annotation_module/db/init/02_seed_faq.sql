INSERT INTO customer_db.question_answers (question, answer) VALUES
('How do I view my energy consumption?', 'To view your energy consumption, navigate to the Monitoring section in your dashboard. There you can see real-time consumption data for all your devices, as well as historical usage patterns.'),

('What is an overconsumption alert?', 'An overconsumption alert is a notification that triggers when any of your devices exceeds its predefined hourly energy consumption limit. You can view these alerts in the Notifications section or receive them in real-time.'),

('How can I reduce my energy consumption?', 'To reduce energy consumption: 1) Monitor your device usage patterns in the Analytics section, 2) Identify devices with high consumption, 3) Schedule high-energy devices during off-peak hours, 4) Regularly check for overconsumption alerts and address them promptly.'),

('How do I add a new device?', 'Only administrators can add new devices to the system. Please contact your system administrator to request adding a new device. They will need the device name, type, and maximum hourly consumption limit.'),

('What does the device monitoring show?', 'Device monitoring displays real-time energy consumption data for each of your assigned devices. It shows current consumption, hourly averages, and alerts you when consumption exceeds predefined thresholds.'),

('How often is consumption data updated?', 'Consumption data is updated in real-time as sensors report measurements. Typically, you will see updates every few seconds, depending on your device configuration and sensor settings.'),

('What is maximum hourly consumption?', 'Maximum hourly consumption is a threshold set for each device that defines the acceptable energy usage limit per hour. When a device exceeds this limit, the system generates an overconsumption alert to notify you.'),

('How can I see my device history?', 'To view device history, go to the Monitoring section and select a specific device. You can then choose a date range to see historical consumption data, patterns, and any overconsumption events that occurred.'),

('Why am I getting too many alerts?', 'If you are receiving frequent overconsumption alerts, it may indicate that: 1) Your device consumption limits are set too low, 2) A device is malfunctioning, or 3) Usage patterns have changed. Contact your administrator to review and adjust the limits.'),

('How do I contact support?', 'You can contact support through this chat interface. For predefined questions, select from the available options. For custom inquiries, type your message and our AI assistant or an administrator will respond to help you.')

ON CONFLICT DO NOTHING;

