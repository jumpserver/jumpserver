function selectAll(){
 var checklist = document.getElementsByName ("selected");
   if(document.getElementById("select_all").checked)
   {
   for(var i=0;i<checklist.length;i++)
   {
      checklist[i].checked = 1;
   }
 }else{
  for(var j=0;j<checklist.length;j++)
  {
     checklist[j].checked = 0;
  }
 }
}
