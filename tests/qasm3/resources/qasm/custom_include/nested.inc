def nested_routine(qubit[3] q) { 
  for int i in [0:2] { 
    h q[i]; 
    x q[i]; 
  } 
}

