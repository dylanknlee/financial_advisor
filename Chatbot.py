import streamlit as st
import time
from openai import OpenAI
import yfinance as yf
from matplotlib import pyplot as plt
import pandas as pd
from utils import steering_agent, stock_information_agent, get_stock_news, get_stock_info, get_tabular_data, get_pe_ratios

# Show title and description.
st.title("💬 Financial Advisor 💵📈")
st.write(
   "Hi there! 👋 I am a chatbot created specifically to provide financial advice! Please ask me any inquiries regarding managing personal financies, stocks, or the economy, and I'd be happy to help!"
)

# Sidebar
def show_prompt_menu():
    st.sidebar.title("📝 What to ask?")
    st.sidebar.markdown("""
    Feel free to ask me about: \n
      1.) General questions about stocks and finances. \n
      2.) Stock and financial analysis of a desired company. \n
      3.) Price-to-Earnings ratios of various companies. \n
      4.) Financial and stock-related news about a given company.
    """)
show_prompt_menu()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def stream_message(message):
    for word in message.split(" "):
        yield word.replace("$", "\\$") + " "  # Escape $ to avoid LateX formatting
        time.sleep(0.03)

if user_input := st.chat_input("Let's talk finance!"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
      st.write_stream(stream_message(user_input))
   
    with st.status("Generating response...", expanded=True) as status:
      st.write("Thinking stocks and finance...") 

   # Display assistant response in chat message container
    with st.chat_message("assistant"):
      try:
        answer = steering_agent(user_input)
        if answer == 1:
          response = stock_information_agent(user_input)
          status.update(
            label="Answered!", state="complete", expanded=False
          )
          st.write_stream(stream_message(response))
        elif answer == 2:
           response = get_stock_info(user_input)
           company_trend = get_tabular_data(user_input)
           company_trend = company_trend.reset_index()
           status.update(
              label="Answered!", state="complete", expanded=False
           )
           # **Create the plot**
           fig, ax = plt.subplots(figsize=(10, 5))
           symbol = company_trend.columns[1]
           ax.plot(company_trend["Date"], company_trend[symbol], linestyle='-', color='red', label=f"{symbol} Stock Price")
           ax.set_xlabel("Date")
           ax.set_ylabel("Stock Price")
           ax.legend()

           # **Display the plot before the streamed response**
           st.pyplot(fig)
           st.write_stream(stream_message(response))
        elif answer == 3:
          response = get_stock_news(user_input)
          status.update(
            label="Answered!", state="complete", expanded=False
          )
          st.write_stream(stream_message(response))
        elif answer == 4:
           response = get_pe_ratios()
           status.update(
            label="Answered!", state="complete", expanded=False
           )
           st.write_stream(stream_message(response))
        elif answer == 5:
           response = "Sorry, I am unequipped to answer that question! Please re-phrase or provide an inquiry more closely related to stocks!"
           st.write_stream(stream_message(response))
      except Exception as e:
        error_message = "Sorry, I ran into an unexpected error! Please rephrase your question. As a reminder, I am tailored to answer most questions specific to finances and stocks!"
        st.write_stream(stream_message(error_message))
      
      # Add assistant response to chat history
      previous_response = "".join(stream_message(response))
      st.session_state.messages.append({"role": "assistant", "content": previous_response})

