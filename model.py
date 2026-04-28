import mysql.connector

mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  password="root",
  database="lab_reactor_management"
)

mycursor = mydb.cursor()

mycursor.execute("CREATE TABLE IF NOT EXISTS experimental_data (id INT AUTO_INCREMENT PRIMARY KEY,  external_temp FLOAT, internal_temp FLOAT, pressure FLOAT, ph_level FLOAT, rotor_rpm INT, stage VARCHAR(255), timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
mycursor.execute("CREATE TABLE IF NOT EXISTS process (id INT AUTO_INCREMENT PRIMARY KEY,  name VARCHAR(255), type VARCHAR(255))")
mycursor.execute("CREATE TABLE IF NOT EXISTS stage (id INT AUTO_INCREMENT PRIMARY KEY,  name VARCHAR(255))")
#mycursor.execute("ALTER TABLE process ADD COLUMN stage_id INT")
#mycursor.execute("ALTER TABLE process ADD FOREIGN KEY (stage_id) REFERENCES stage(id)")
#mycursor.execute("ALTER TABLE stage ADD COLUMN process_id INT;")
#mycursor.execute("ALTER TABLE experimental_data ADD COLUMN stage_id INT;")
#mycursor.execute("ALTER TABLE experimental_data ADD COLUMN duration INT;")
mycursor.execute("CREATE TABLE IF NOT EXISTS control_data (id INT AUTO_INCREMENT PRIMARY KEY,  external_temp FLOAT, internal_temp FLOAT, pressure FLOAT, ph_level FLOAT, rotor_rpm INT, duration INT, stage_id INT, FOREIGN KEY (stage_id) REFERENCES stage(id))")