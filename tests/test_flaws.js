// Flaw 1: Using eval
function useEval() {
    var userInput = "alert('Hello World');"; // User input might be malicious
    eval(userInput); // Dangerous! eval executes arbitrary code.
}

// Flaw 2: Using document.write
function useDocumentWrite() {
    document.write("<h1>Hello, World!</h1>"); // document.write can be abused, especially if used dynamically.
}

// Flaw 3: Using setInterval with potentially unsafe code
function useSetInterval() {
    setInterval(function() {
        alert("This is a repetitive message!");
    }, 1000); // setInterval can be used maliciously to create infinite loops or excessive load.
}

// Flaw 4: Using setTimeout with potentially unsafe code
function useSetTimeout() {
    setTimeout(function() {
        alert("This is a delayed message!");
    }, 2000); // setTimeout with eval or dangerous functions can be abused for various attacks.
}

// Flaw 5: Using innerHTML with untrusted data
function useInnerHTML() {
    var userInput = "<img src='x' onerror='alert(\"Hacked!\")'>";
    document.getElementById("container").innerHTML = userInput; // Using innerHTML with untrusted input can lead to XSS.
}

// Call functions to invoke the flaws
useEval();
useDocumentWrite();
useSetInterval();
useSetTimeout();
useInnerHTML();