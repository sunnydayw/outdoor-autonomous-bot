# commands.py

'''
Define single-letter commands that will be sent by the PC over the
   serial link.
'''

# Single-letter commands:
CMD_SET_SPEEDS     = 'm'   # e.g. 'm leftSpeed rightSpeed'
CMD_READ_ENCODERS  = 'e'
CMD_RESET_ENCODERS = 'r'
# ... add as needed

# For convenience, define motor indices
LEFT = 0
RIGHT = 1
