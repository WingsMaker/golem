# Golem chatbot framework

![PyPI](https://img.shields.io/pypi/v/django-golem.svg)

<p align="center">
<img src="https://www.praguevisitor.eu/wp-content/uploads/2018/03/Golem.jpg" width="300"/>
</p>

#### Golem is a python framework for building chatbots for Messenger, Telegram and other platforms.

It differs from other bot frameworks by giving a concrete structure to the conversation.

What it can do:
- __Receive messages__ from __Messenger__ and __Telegram__ (Actions on Google coming soon)
- __Extract entities__ from these messages, for example using [Wit.ai](http://wit.ai)
  - e.g. "Show me the best concert" -> *intent:* recommend, *query:* concert
- __Keep track of the history__ of all entity values in the *context*
- __Move between different states__ of the conversation based on intent and other entities
- Call your functions for each state and __send messages__ and media back to the user
- It supports any language supported by Wit (English is recommended)
- Golem now has its own __web GUI__ for easy testing

What it can NOT do:
- It does not pre-train Wit, you have to do that yourself
- It's not built for AI conversational bots (you can try though :P)

## Getting started

Just install the package and run our `golm` init script that will take care of initial configuration.
```bash
pip3 install django-golem
golm init my-bot
cd my-bot && golm start my-bot
```

That's all! A development chat server should now be running at http://localhost:8000.


You may also want to configure NLU, chat integrations and analytics, see the documentation for details.

## Docs

It's very easy to get started!

Find out how to make your own bot on the **[Wiki](https://github.com/prihoda/golem/wiki)**.


## Authors
- David Příhoda - [prihoda](https://github.com/prihoda)
- Jakub Drdák   - [drdakjak](https://github.com/drdakjak)
- Matúš Žilinec - [mzilinec](https://github.com/mzilinec)

Made @ [Datalab](https://datalab.fit.cvut.cz) [FIT CTU](https://fit.cvut.cz/en) in Prague.
