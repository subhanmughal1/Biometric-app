
class User():
    id = ""
    name = ""
    mobile = ""
    fatherName = ""
    computerNumber = ""
    image = ""
    fee = ""
    pay = ""
    type = ""
    note = ""
    balance = ""
    def __init__(self,id='',name='',fatherName='',computerNumber='',image='',note='',pay='',fee='',type='',balance=''):
        self.id=id
        self.name=name
        self.fatherName=fatherName
        self.computerNumber=computerNumber
        self.image=image
        self.note=note
        self.pay=pay
        self.fee=fee
        self.type=type
        self.balance=balance