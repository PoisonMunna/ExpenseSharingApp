"""
Expense Sharing App - Splitwise Style
Track shared expenses, calculate balances, and simplify debts
Author: Python Learning Project
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import sys
import argparse

class User:
    """Represents a user in the expense sharing system"""
    
    def __init__(self, name: str, email: str = ""):
        self.name = name
        self.email = email
        self.balance = 0.0  # Net balance (positive = owed, negative = owes)
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'email': self.email,
            'balance': self.balance
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'User':
        user = cls(data['name'], data.get('email', ''))
        user.balance = data.get('balance', 0.0)
        return user

class Expense:
    """Represents an expense in the system"""
    
    def __init__(self, description: str, amount: float, paid_by: str, 
                 split_type: str = "equal", participants: List[str] = None,
                 shares: Dict[str, float] = None):
        self.description = description
        self.amount = amount
        self.paid_by = paid_by
        self.split_type = split_type  # "equal", "percentage", "exact"
        self.participants = participants or []
        self.shares = shares or {}
        self.date = datetime.now()
        self.expense_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(hash(description))[-4:]
    
    def to_dict(self) -> Dict:
        return {
            'expense_id': self.expense_id,
            'description': self.description,
            'amount': self.amount,
            'paid_by': self.paid_by,
            'split_type': self.split_type,
            'participants': self.participants,
            'shares': self.shares,
            'date': self.date.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Expense':
        expense = cls(
            data['description'],
            data['amount'],
            data['paid_by'],
            data['split_type'],
            data.get('participants', []),
            data.get('shares', {})
        )
        expense.expense_id = data.get('expense_id', '')
        expense.date = datetime.fromisoformat(data['date']) if 'date' in data else datetime.now()
        return expense

class Group:
    """Represents a group for expense sharing"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.members: List[User] = []
        self.expenses: List[Expense] = []
        self.created_date = datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'description': self.description,
            'members': [user.to_dict() for user in self.members],
            'expenses': [expense.to_dict() for expense in self.expenses],
            'created_date': self.created_date.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Group':
        group = cls(data['name'], data.get('description', ''))
        
        for member_data in data.get('members', []):
            group.members.append(User.from_dict(member_data))
        
        for expense_data in data.get('expenses', []):
            group.expenses.append(Expense.from_dict(expense_data))
        
        return group
    
    def add_member(self, user: User):
        """Add a member to the group"""
        if not any(m.name == user.name for m in self.members):
            self.members.append(user)
            return True
        return False
    
    def remove_member(self, user_name: str) -> bool:
        """Remove a member from the group"""
        for i, member in enumerate(self.members):
            if member.name == user_name:
                self.members.pop(i)
                return True
        return False
    
    def add_expense(self, expense: Expense):
        """Add an expense to the group"""
        self.expenses.append(expense)
        self.update_balances()
    
    def update_balances(self):
        """Update all user balances based on expenses"""
        # Reset all balances
        for member in self.members:
            member.balance = 0.0
        
        # Calculate balances
        for expense in self.expenses:
            # Get participants
            participants = expense.participants if expense.participants else [m.name for m in self.members]
            
            # Calculate shares
            shares = {}
            if expense.split_type == "equal":
                share_amount = expense.amount / len(participants)
                for participant in participants:
                    shares[participant] = share_amount
            
            elif expense.split_type == "percentage":
                for participant, percentage in expense.shares.items():
                    shares[participant] = (percentage / 100) * expense.amount
            
            elif expense.split_type == "exact":
                shares = expense.shares.copy()
            
            # Update balances
            for participant, amount in shares.items():
                if participant != expense.paid_by:
                    # Find user and update balance
                    for member in self.members:
                        if member.name == expense.paid_by:
                            member.balance += amount
                        if member.name == participant:
                            member.balance -= amount
    
    def simplify_debts(self) -> List[Dict]:
        """
        Simplify debts using the minimum transaction algorithm
        Returns list of simplified transactions
        """
        # Get current balances
        balances = {member.name: member.balance for member in self.members}
        
        # Separate positive and negative balances
        positive = [(name, amount) for name, amount in balances.items() if amount > 0.01]
        negative = [(name, -amount) for name, amount in balances.items() if amount < -0.01]
        
        transactions = []
        i = j = 0
        
        while i < len(positive) and j < len(negative):
            name_from, amount_owed = negative[j]  # Person who owes
            name_to, amount_owned = positive[i]   # Person who is owed
            
            amount = min(amount_owed, amount_owned)
            
            if amount > 0.01:
                transactions.append({
                    'from': name_from,
                    'to': name_to,
                    'amount': round(amount, 2)
                })
            
            # Update remaining amounts
            if amount_owed > amount_owned:
                negative[j] = (name_from, amount_owed - amount_owned)
                i += 1
            elif amount_owed < amount_owned:
                positive[i] = (name_to, amount_owned - amount_owed)
                j += 1
            else:
                i += 1
                j += 1
        
        return transactions
    
    def get_summary(self) -> Dict:
        """Get group summary statistics"""
        total_expenses = sum(e.amount for e in self.expenses)
        total_members = len(self.members)
        
        member_balances = {member.name: round(member.balance, 2) for member in self.members}
        
        return {
            'group_name': self.name,
            'total_members': total_members,
            'total_expenses': total_expenses,
            'number_of_expenses': len(self.expenses),
            'member_balances': member_balances
        }

class ExpenseApp:
    """Main application class"""
    
    def __init__(self, data_file: str = "expenses.json"):
        self.data_file = data_file
        self.groups: List[Group] = []
        self.current_group: Optional[Group] = None
        self.load_data()
    
    def load_data(self):
        """Load data from JSON file"""
        if not os.path.exists(self.data_file):
            print("📚 No existing data found. Starting fresh!")
            return
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for group_data in data.get('groups', []):
                group = Group.from_dict(group_data)
                self.groups.append(group)
            
            print(f"✅ Loaded {len(self.groups)} groups")
            
            if self.groups:
                self.current_group = self.groups[0]
                print(f"✅ Current group: {self.current_group.name}")
                
        except Exception as e:
            print(f"❌ Error loading data: {e}")
    
    def save_data(self):
        """Save data to JSON file"""
        try:
            data = {
                'groups': [group.to_dict() for group in self.groups]
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("✅ Data saved successfully!")
        except Exception as e:
            print(f"❌ Error saving data: {e}")
    
    def create_group(self):
        """Create a new group"""
        print("\n" + "="*60)
        print("➕ CREATE NEW GROUP")
        print("="*60)
        
        name = input("\n📝 Group name: ").strip()
        if not name:
            print("❌ Group name cannot be empty!")
            return
        
        description = input("📋 Description (optional): ").strip()
        
        group = Group(name, description)
        self.groups.append(group)
        self.current_group = group
        
        print(f"\n✅ Group '{name}' created successfully!")
        self.save_data()
    
    def switch_group(self):
        """Switch to a different group"""
        if not self.groups:
            print("❌ No groups available. Create one first!")
            return
        
        print("\n" + "="*60)
        print("🔄 SWITCH GROUP")
        print("="*60)
        
        print("\n📂 Available groups:")
        for i, group in enumerate(self.groups, 1):
            print(f"  {i}. {group.name} ({len(group.members)} members)")
        
        try:
            choice = int(input("\n👉 Select group number: ")) - 1
            if 0 <= choice < len(self.groups):
                self.current_group = self.groups[choice]
                print(f"\n✅ Switched to group: {self.current_group.name}")
            else:
                print("❌ Invalid selection!")
        except ValueError:
            print("❌ Please enter a valid number!")
    
    def add_member(self):
        """Add a member to current group"""
        if not self.current_group:
            print("❌ No group selected. Create or switch to a group first!")
            return
        
        print("\n" + "="*60)
        print("👤 ADD MEMBER")
        print("="*60)
        
        name = input("\n📝 Member name: ").strip()
        if not name:
            print("❌ Name cannot be empty!")
            return
        
        email = input("📧 Email (optional): ").strip()
        
        user = User(name, email)
        if self.current_group.add_member(user):
            print(f"\n✅ Added {name} to group '{self.current_group.name}'")
            self.save_data()
        else:
            print(f"\n⚠️ {name} is already in this group!")
    
    def add_expense(self):
        """Add an expense to current group"""
        if not self.current_group:
            print("❌ No group selected. Create or switch to a group first!")
            return
        
        if not self.current_group.members:
            print("❌ No members in group. Add some members first!")
            return
        
        print("\n" + "="*60)
        print("💰 ADD EXPENSE")
        print("="*60)
        
        description = input("\n📝 Description: ").strip()
        if not description:
            print("❌ Description cannot be empty!")
            return
        
        try:
            amount = float(input("💵 Amount: "))
            if amount <= 0:
                print("❌ Amount must be greater than 0!")
                return
        except ValueError:
            print("❌ Invalid amount!")
            return
        
        # Show members
        print("\n👥 Members:")
        for i, member in enumerate(self.current_group.members, 1):
            print(f"  {i}. {member.name}")
        
        try:
            paid_by_idx = int(input("\n👤 Who paid? (select number): ")) - 1
            if not (0 <= paid_by_idx < len(self.current_group.members)):
                print("❌ Invalid selection!")
                return
            paid_by = self.current_group.members[paid_by_idx].name
        except ValueError:
            print("❌ Invalid selection!")
            return
        
        # Split type
        print("\n📌 Split type:")
        print("  1. Equal (split equally among participants)")
        print("  2. Percentage (split by percentage)")
        print("  3. Exact (custom amounts)")
        
        split_choice = input("\n👉 Choose (1-3): ").strip()
        
        split_type = "equal"
        participants = [m.name for m in self.current_group.members]
        shares = {}
        
        if split_choice == '2':
            split_type = "percentage"
            print("\n📊 Enter percentage for each participant (total must be 100):")
            total_percentage = 0
            for member in self.current_group.members:
                try:
                    perc = float(input(f"  {member.name} (%): "))
                    if perc < 0:
                        print("❌ Percentage cannot be negative!")
                        return
                    shares[member.name] = perc
                    total_percentage += perc
                except ValueError:
                    print("❌ Invalid percentage!")
                    return
            
            if abs(total_percentage - 100) > 0.01:
                print(f"❌ Total percentage is {total_percentage}, must be 100!")
                return
        
        elif split_choice == '3':
            split_type = "exact"
            print("\n💰 Enter exact amount for each participant:")
            total_shares = 0
            for member in self.current_group.members:
                try:
                    share = float(input(f"  {member.name}: ₹"))
                    if share < 0:
                        print("❌ Amount cannot be negative!")
                        return
                    shares[member.name] = share
                    total_shares += share
                except ValueError:
                    print("❌ Invalid amount!")
                    return
            
            if abs(total_shares - amount) > 0.01:
                print(f"❌ Total shares is {total_shares}, must be {amount}!")
                return
        
        else:  # Equal split
            split_type = "equal"
            shares = {}
            share_amount = amount / len(participants)
            for participant in participants:
                shares[participant] = share_amount
        
        # Create expense
        expense = Expense(description, amount, paid_by, split_type, participants, shares)
        self.current_group.add_expense(expense)
        
        print(f"\n✅ Expense added successfully!")
        print(f"   Description: {description}")
        print(f"   Amount: ₹{amount}")
        print(f"   Paid by: {paid_by}")
        
        self.save_data()
    
    def show_balances(self):
        """Show current balances in the group"""
        if not self.current_group:
            print("❌ No group selected. Create or switch to a group first!")
            return
        
        if not self.current_group.members:
            print("❌ No members in group!")
            return
        
        print("\n" + "="*60)
        print(f"💰 BALANCES - {self.current_group.name}")
        print("="*60)
        
        # Update balances
        self.current_group.update_balances()
        
        # Show member balances
        print("\n👥 Member Balances:")
        print("-"*40)
        for member in sorted(self.current_group.members, key=lambda x: x.balance, reverse=True):
            balance = member.balance
            if balance > 0:
                status = f"is owed ₹{balance:.2f}"
            elif balance < 0:
                status = f"owes ₹{abs(balance):.2f}"
            else:
                status = "settled up"
            print(f"  {member.name}: {status}")
        
        # Show simplified debts
        print("\n🔄 Simplified Debts:")
        print("-"*40)
        transactions = self.current_group.simplify_debts()
        if transactions:
            for tx in transactions:
                print(f"  {tx['from']} → {tx['to']}: ₹{tx['amount']:.2f}")
        else:
            print("  ✅ Everyone is settled up!")
        
        self.save_data()
    
    def show_summary(self):
        """Show group summary"""
        if not self.current_group:
            print("❌ No group selected. Create or switch to a group first!")
            return
        
        summary = self.current_group.get_summary()
        
        print("\n" + "="*60)
        print(f"📊 GROUP SUMMARY - {summary['group_name']}")
        print("="*60)
        print(f"👥 Total Members: {summary['total_members']}")
        print(f"💰 Total Expenses: ₹{summary['total_expenses']:.2f}")
        print(f"📝 Number of Expenses: {summary['number_of_expenses']}")
        print("\nMember Balances:")
        print("-"*40)
        for name, balance in summary['member_balances'].items():
            if balance > 0:
                status = f"is owed ₹{balance:.2f}"
            elif balance < 0:
                status = f"owes ₹{abs(balance):.2f}"
            else:
                status = "settled up"
            print(f"  {name}: {status}")
    
    def settle_up(self):
        """Settle up - mark a debt as paid"""
        if not self.current_group:
            print("❌ No group selected. Create or switch to a group first!")
            return
        
        print("\n" + "="*60)
        print("💳 SETTLE UP")
        print("="*60)
        
        transactions = self.current_group.simplify_debts()
        if not transactions:
            print("✅ Everyone is settled up!")
            return
        
        print("\n📋 Outstanding debts:")
        for i, tx in enumerate(transactions, 1):
            print(f"  {i}. {tx['from']} owes {tx['to']} ₹{tx['amount']:.2f}")
        
        try:
            choice = int(input("\n👉 Select debt to settle (number): ")) - 1
            if not (0 <= choice < len(transactions)):
                print("❌ Invalid selection!")
                return
            
            tx = transactions[choice]
            
            confirm = input(f"\n✅ Confirm settlement: {tx['from']} pays {tx['to']} ₹{tx['amount']:.2f}? (y/n): ")
            if confirm.lower() == 'y':
                # Create a settlement expense
                expense = Expense(
                    f"Settlement: {tx['from']} → {tx['to']}",
                    tx['amount'],
                    tx['from'],
                    "equal",
                    [tx['to']]
                )
                self.current_group.add_expense(expense)
                self.save_data()
                print(f"\n✅ Settlement recorded!")
        
        except ValueError:
            print("❌ Invalid selection!")
    
    def list_expenses(self):
        """List all expenses in the group"""
        if not self.current_group:
            print("❌ No group selected. Create or switch to a group first!")
            return
        
        if not self.current_group.expenses:
            print("📭 No expenses recorded yet!")
            return
        
        print("\n" + "="*60)
        print(f"📋 EXPENSES - {self.current_group.name}")
        print("="*60)
        
        for i, expense in enumerate(reversed(self.current_group.expenses), 1):
            print(f"\n{i}. {expense.description}")
            print(f"   Amount: ₹{expense.amount:.2f}")
            print(f"   Paid by: {expense.paid_by}")
            print(f"   Date: {expense.date.strftime('%Y-%m-%d %H:%M')}")
            print(f"   Split: {expense.split_type}")
            if expense.split_type == "equal":
                print(f"   Split equally among {len(expense.participants)}")
            elif expense.split_type == "percentage":
                print("   Split by percentage:")
                for participant, percentage in expense.shares.items():
                    print(f"     {participant}: {percentage}%")
            elif expense.split_type == "exact":
                print("   Split by exact amounts:")
                for participant, amount in expense.shares.items():
                    print(f"     {participant}: ₹{amount:.2f}")
    
    def delete_expense(self):
        """Delete an expense"""
        if not self.current_group:
            print("❌ No group selected!")
            return
        
        if not self.current_group.expenses:
            print("📭 No expenses to delete!")
            return
        
        print("\n" + "="*60)
        print("🗑️ DELETE EXPENSE")
        print("="*60)
        
        self.list_expenses()
        
        try:
            choice = int(input("\n👉 Select expense to delete (number): ")) - 1
            if 0 <= choice < len(self.current_group.expenses):
                expense = self.current_group.expenses[choice]
                confirm = input(f"Delete '{expense.description}'? (y/n): ")
                if confirm.lower() == 'y':
                    self.current_group.expenses.pop(choice)
                    self.current_group.update_balances()
                    self.save_data()
                    print("✅ Expense deleted!")
            else:
                print("❌ Invalid selection!")
        except ValueError:
            print("❌ Invalid selection!")

def main():
    """Main application entry point"""
    app = ExpenseApp()
    
    print("\n" + "="*60)
    print("💰 EXPENSE SHARING APP - Splitwise Style")
    print("="*60)
    
    while True:
        print("\n📌 MAIN MENU")
        print("="*40)
        
        if app.current_group:
            print(f"📂 Current Group: {app.current_group.name}")
            print(f"👥 Members: {len(app.current_group.members)}")
            print(f"💰 Expenses: {len(app.current_group.expenses)}")
        else:
            print("📂 No group selected")
        
        print("\n" + "="*40)
        print("1. 📁 Create Group")
        print("2. 🔄 Switch Group")
        print("3. 👤 Add Member")
        print("4. 💰 Add Expense")
        print("5. 💵 Show Balances")
        print("6. 📊 Show Summary")
        print("7. 💳 Settle Up")
        print("8. 📋 List Expenses")
        print("9. 🗑️ Delete Expense")
        print("10. 🚪 Exit")
        print("="*40)
        
        choice = input("\n👉 Enter your choice (1-10): ").strip()
        
        if choice == '1':
            app.create_group()
        elif choice == '2':
            app.switch_group()
        elif choice == '3':
            app.add_member()
        elif choice == '4':
            app.add_expense()
        elif choice == '5':
            app.show_balances()
        elif choice == '6':
            app.show_summary()
        elif choice == '7':
            app.settle_up()
        elif choice == '8':
            app.list_expenses()
        elif choice == '9':
            app.delete_expense()
        elif choice == '10':
            print("\n👋 Thanks for using Expense Sharing App!")
            break
        else:
            print("❌ Invalid choice!")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Application closed")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)