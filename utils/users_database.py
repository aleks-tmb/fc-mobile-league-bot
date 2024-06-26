import csv

class UsersDatabaseCSV:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = []
        with open(self.file_path, mode='r', newline='') as file:
            reader = csv.DictReader(file)
            self.data = [row for row in reader]
            for row in self.data:
                row['ID'] = int(row['ID'])
                row['rate'] = int(row['rate'])

    def get_all_users(self):
        """Returns the list of users."""
        return self.data

    def get_user(self, key, key_type = 'ID'):
        if key_type == 'ID':
            key = int(key)
        for user in self.data:
            if user[key_type] == key:
                return user
        raise KeyError(f"User with {key_type} = {key} not found.")

    def get_username_by_id(self, user_id):
        try:
            return self.get_user(user_id)['username']
        except:
            return ""

    def get_id_by_username(self, username):
        return self.get_user(username,'username')['ID']


    def add_user(self, id, username):
        user = {
            "ID": id,
            "username": username,
            "rate": 0,
            "league": ""
        }          

        user_id = user.get('ID')
        if user_id is None:
            raise ValueError("User data must contain an 'ID' field.")
        
        # Check if a user with the same ID already exists
        if any(existing_user['ID'] == user_id for existing_user in self.data):
            return
        
        self.data.append(user)
        self._save_data()

    def update_user(self, updated_user):   
        for i, user in enumerate(self.data):
            if user['ID'] == updated_user['ID']:
                self.data[i] = updated_user
                self._save_data()
                return
        print(f"User with ID {updated_user['ID']} not found.")

    def delete_user(self, user_id):
        user_id = str(user_id) 

        for i, user in enumerate(self.data):
            print(user)
            if user['ID'] == user_id:
                del self.data[i]
                self._save_data()
                return
        print(f"User with ID {user_id} not found.")

    def _save_data(self):
        """Writes the current data to the CSV file."""
        with open(self.file_path, mode='w', newline='') as file:
            if self.data:
                fieldnames = self.data[0].keys()
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.data)
            else:
                writer = csv.DictWriter(file, fieldnames=[])
                writer.writeheader()

    def get_rating_table(self):
        sorted_users = sorted(self.data, key=lambda x: x['rate'], reverse=True)

        respond = "Рейтинг Лиги\n\n"
        for i, participant in enumerate(sorted_users, start=1):
            respond += f"{i}. {participant['username']} [{participant['rate']}]\n"
        return respond
