// ----------------------
// UTILIDADES API
// ----------------------
async function apiRequest(endpoint, method = 'POST', data = {}) {
  const response = await fetch(`/api/${endpoint}`, {
    method,
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  });

  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(result.message || 'Error en la petición');
  }

  return result;
}

// ----------------------
// CAMBIAR LOGIN/REGISTRO
// ----------------------
function toggleForm(){

  document
  .querySelector(".login-form")
  .classList.toggle("active");

  document
  .querySelector(".register-form")
  .classList.toggle("active");
}

// ----------------------
// MOSTRAR/OCULTAR PASSWORD
// ----------------------
function togglePassword(id, icon){

  let input = document.getElementById(id);

  if(input.type === "password"){

    input.type = "text";

    icon.classList.remove("fa-eye");
    icon.classList.add("fa-eye-slash");

  }else{

    input.type = "password";

    icon.classList.remove("fa-eye-slash");
    icon.classList.add("fa-eye");
  }
}

// ----------------------
// VALIDACIONES
// ----------------------
function setError(input,message,errorId){

  input.classList.add("error");
  input.classList.remove("success");

  document
  .getElementById(errorId)
  .innerText = message;
}

function setSuccess(input,errorId){

  input.classList.remove("error");
  input.classList.add("success");

  document
  .getElementById(errorId)
  .innerText = "";
}

// ----------------------
// LOGIN
// ----------------------
async function login(){

  let email = document.getElementById("loginEmail");

  let pass = document.getElementById("loginPass");

  let valid = true;

  // EMAIL
  if(email.value.trim() === ""){

    setError(
      email,
      "Campo requerido",
      "loginEmailError"
    );

    valid = false;

  }else{

    setSuccess(email,"loginEmailError");
  }

  // PASSWORD
  if(pass.value.trim() === ""){

    setError(
      pass,
      "Campo requerido",
      "loginPassError"
    );

    valid = false;

  }else{

    setSuccess(pass,"loginPassError");
  }

  if(!valid) return;

  try {
    const result = await apiRequest('login', 'POST', {
      email: email.value.trim(),
      password: pass.value
    });

    sessionStorage.setItem('sublimeUser', JSON.stringify(result.user));
    window.location.href = '/admin';
  } catch (error) {
    alert(error.message || 'Credenciales incorrectas');
  }
}

// ----------------------
// REGISTRO
// ----------------------
async function register(){

  let name = document.getElementById("regName");

  let email = document.getElementById("regEmail");

  let pass = document.getElementById("regPass");

  let pass2 = document.getElementById("regPass2");

  let valid = true;

  // NOMBRE
  if(name.value.trim() === ""){

    setError(
      name,
      "Campo requerido",
      "regNameError"
    );

    valid = false;

  }else{

    setSuccess(name,"regNameError");
  }

  // EMAIL
  if(!email.value.includes("@")){

    setError(
      email,
      "Email inválido",
      "regEmailError"
    );

    valid = false;

  }else{

    setSuccess(email,"regEmailError");
  }

  // PASSWORD
  if(pass.value.length < 4){

    setError(
      pass,
      "Mínimo 4 caracteres",
      "regPassError"
    );

    valid = false;

  }else{

    setSuccess(pass,"regPassError");
  }

  // CONFIRMAR PASSWORD
  if(pass.value !== pass2.value){

    setError(
      pass2,
      "No coinciden",
      "regPass2Error"
    );

    valid = false;

  }else{

    setSuccess(pass2,"regPass2Error");
  }

  if(!valid) return;

  try {
    await apiRequest('register', 'POST', {
      name: name.value.trim(),
      email: email.value.trim(),
      password: pass.value
    });

    alert('Registro exitoso');
    toggleForm();
  } catch (error) {
    alert(error.message || 'No se pudo registrar');
  }
}

// ----------------------
// ABRIR MODAL
// ----------------------
function showRecover(){

  document
  .getElementById("recoverModal")
  .style.display = "flex";
}

// ----------------------
// CERRAR MODAL
// ----------------------
function closeRecover(){

  document
  .getElementById("recoverModal")
  .style.display = "none";
}

// ----------------------
// RECUPERAR PASSWORD
// ----------------------
async function recoverPassword(){
  const emailInput = document.getElementById('recoverEmail');
  const passInput = document.getElementById('recoverPass');

  const email = emailInput.value.trim();
  const newPassword = passInput.value;

  if (!email) {
    alert('Ingresa tu correo electrónico.');
    return;
  }

  if (newPassword.length < 4) {
    alert('La nueva contraseña debe tener al menos 4 caracteres.');
    return;
  }

  try {
    await apiRequest('recover', 'POST', {
      email,
      password: newPassword
    });

    alert('Contraseña actualizada con éxito. Ahora puedes iniciar sesión.');
    emailInput.value = '';
    passInput.value = '';
    closeRecover();
  } catch (error) {
    alert(error.message || 'No se pudo cambiar la contraseña.');
  }
}